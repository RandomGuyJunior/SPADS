package RapidMods;
use strict;
use warnings;
use SpadsPluginApi;
use JSON::PP qw(encode_json decode_json);

my $pluginVersion = '0.1';
my $requiredSpadsVersion = '0.11.4';
my %params = (commandsFile => ['notNull'], helpFile => ['notNull']);
my $busy = 0;
my $stateFile = '/srv/spads/var/rapidmods-downloaded.json';
my %downloaded;

sub loadDownloaded {
  %downloaded = ();
  return unless -f $stateFile;
  if(open my $fh, '<', $stateFile) {
    local $/;
    my $raw = <$fh>;
    close $fh;
    eval {
      my $data = decode_json($raw);
      if(ref($data) eq 'HASH' && ref($data->{tags}) eq 'ARRAY') {
        for my $tag (@{$data->{tags}}) {
          $downloaded{$tag} = 1 if defined($tag) && $tag =~ /\A[A-Za-z0-9_-]+:[A-Za-z0-9_-]+\z/;
        }
      }
    };
    slog("RapidMods state file unreadable: $@",2) if $@;
  }
}

sub saveDownloaded {
  my $temp = "$stateFile.tmp.$";
  if(open my $fh, '>', $temp) {
    print {$fh} encode_json({schema_version => 1, tags => [sort keys %downloaded]});
    close $fh;
    if(!rename($temp,$stateFile)) {
      slog("RapidMods state file rename failed: $!",2);
      unlink $temp;
    }
  } else { slog("RapidMods state file write failed: $!",2); }
}

sub hModStatus {
  my ($source,$user,$p_params,$checkOnly) = @_;
  return 1 if $checkOnly;
  # Private reply is intentional: do not flood battle chat on every join.
  # These tags are server-downloaded, NOT necessarily activated for this battle.
  my $tags = join(',',sort keys %downloaded);
  sayPrivate($user,"[RapidModsState] downloaded=$tags") if(getLobbyState() > 3);
  return 1;
}


# Register once per opened battle with TEI's private capability protocol.
# The capability is never posted to battle chat.
sub onBattleOpened {
  queueLobbyCommand(['c.battle.mod_capabilities', 'rapid-mods-v1']);
  slog('Requested TEI rapid-mods-v1 capability registration', 3);
  return 1;
}


# SPADS invokes this before checking direct/vote access. Only the battle
# membership held by SPADS can authorize the sole-participant exception.
sub commandRightsOverride {
  my ($self,$command,$params,$source,$user,$level,$originalLevel,$rights) = @_;
  return unless($command eq 'mod' && ($source eq 'battle' || $source eq 'pv'));
  return 1 if(exists $main::bosses{$user});
  my $lobby = getLobbyInterface();
  return unless($lobby && $lobby->{battle} && $lobby->{battle}{users});
  my @participants = grep { $_ ne getSpadsConf()->{lobbyLogin} } keys %{$lobby->{battle}{users}};
  return unless(@participants == 1 && $participants[0] eq $user);
  return 1;
}


sub getVersion { return $pluginVersion }
sub getRequiredSpadsVersion { return $requiredSpadsVersion }
sub getParams { return [\%params, {}] }

sub new {
  my $self = bless({}, shift);
  loadDownloaded();
  addSpadsCommandHandler({mod => \&hMod, modstatus => \&hModStatus});
  slog('RapidMods command handler loaded',3);
  return $self;
}

sub onUnload {
  removeSpadsCommandHandler(['mod','modstatus']);
}

sub hMod {
  my ($source,$user,$p_params,$checkOnly) = @_;
  unless(@$p_params == 1 && $p_params->[0] =~ /\A[A-Za-z0-9_-]+:[A-Za-z0-9_-]+\z/ && length($p_params->[0]) <= 128) {
    ::invalidSyntax($user,'mod');
    return 0;
  }
  my $tag = $p_params->[0];
  if($busy) {
    answer('Another Rapid download is already in progress.');
    return 0;
  }
  my $dataDir = getSpadsConf()->{springDataDir};
  if(!defined($dataDir) || $dataDir eq '' || $dataDir =~ /:/) {
    answer('Rapid installation requires one configured Spring data directory.');
    return 0;
  }
  my $script = '/srv/spads/deploy/download-rapid-mod.py';
  unless(-f $script && -r $script && -d $dataDir && -w $dataDir) {
    answer('Rapid downloader is not deployed or Spring data directory is not writable.');
    return 0;
  }
  return 1 if($checkOnly);
  my $pid = forkProcess(
    sub {
      my $rc = system('python3',$script,$tag,'--data-dir',$dataDir);
      exit($rc == -1 ? 127 : ($rc & 127 ? 128 + ($rc & 127) : ($rc >> 8)));
    },
    sub {
      my ($rc) = @_;
      $busy = 0;
      if($rc == 0) {
        $downloaded{$tag} = 1;
        saveDownloaded();
        slog("Rapid download completed for $tag",3);
        sayBattle("[RapidMods] installed $tag") if(getLobbyState() > 3);
        sayPrivate($user,"Rapid download completed for $tag. Archive refresh may be required.")
          if(getLobbyState() > 3 && exists getLobbyInterface()->{users}->{$user});
      } else {
        slog("Rapid download failed for $tag (exit $rc)",2);
        sayBattle("[RapidMods] failed $tag") if(getLobbyState() > 3);
        sayPrivate($user,"Rapid download failed for $tag (exit $rc). Check SPADS logs.")
          if(getLobbyState() > 3 && exists getLobbyInterface()->{users}->{$user});
      }
    }
  );
  unless($pid) {
    answer('Unable to start Rapid download.');
    return 0;
  }
  $busy = 1;
  sayBattle("[RapidMods] installing $tag") if(getLobbyState() > 3);
  answer("Rapid download started for $tag.");
  return 1;
}
1;
