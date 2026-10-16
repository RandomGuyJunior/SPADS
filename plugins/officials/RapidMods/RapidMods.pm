package RapidMods;
use strict;
use warnings;
use SpadsPluginApi;

my $pluginVersion = '0.1';
my $requiredSpadsVersion = '0.11.4';
my %params = (commandsFile => ['notNull'], helpFile => ['notNull']);
my $busy = 0;

# The client requires a positive capability announcement from the battle founder.
# An official SPADS host does not advertise this protocol.
sub advertiseModHub {
  return 1 unless(getLobbyState() > 5);
  sayBattle('[RapidMods] hub-v1');
  return 1;
}

sub onJoinedBattle { advertiseModHub() }
sub onBattleOpened { advertiseModHub() }


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
  addSpadsCommandHandler({mod => \&hMod});
  # Periodic refresh covers clients which join during the initial announcement.
  addTimer('RapidModsAdvertise',3,8,\&advertiseModHub);
  slog('RapidMods command handler loaded',3);
  return $self;
}

sub onUnload {
  removeSpadsCommandHandler(['mod']);
  removeTimer('RapidModsAdvertise');
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
  answer("Rapid download started for $tag.");
  return 1;
}
1;
