"""Central configuration for SENTINEL-NIDS. Single source of truth for paths, columns, seeds."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"
FIGURES = ROOT / "reports" / "figures"
METRICS = ROOT / "reports" / "metrics"
for _p in (DATA_RAW, DATA_PROC, MODELS, FIGURES, METRICS):
    _p.mkdir(parents=True, exist_ok=True)

SEED = 42

# NSL-KDD mirror (verified reachable 08 Aug 2026). See data/README.md for provenance.
MIRROR = "https://raw.githubusercontent.com/HoaNP/NSL-KDD-DataSet/master/"
FILES = ["KDDTrain+.txt", "KDDTest+.txt", "KDDTrain+_20Percent.txt", "KDDTest-21.txt"]

# 41 features + label + difficulty, per the NSL-KDD/KDD'99 specification.
COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", "land",
    "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    "label", "difficulty",
]
CATEGORICAL = ["protocol_type", "service", "flag"]

# Canonical mapping of the 38 NSL-KDD attack labels to the 4 standard attack families.
# DoS = denial of service | Probe = surveillance/scanning
# R2L = unauthorised remote-to-local access | U2R = unauthorised privilege escalation
ATTACK_FAMILY = {
    "normal": "Normal",
    # --- DoS ---
    "neptune": "DoS", "back": "DoS", "land": "DoS", "pod": "DoS", "smurf": "DoS",
    "teardrop": "DoS", "mailbomb": "DoS", "apache2": "DoS", "processtable": "DoS",
    "udpstorm": "DoS",
    # --- Probe ---
    "ipsweep": "Probe", "nmap": "Probe", "portsweep": "Probe", "satan": "Probe",
    "mscan": "Probe", "saint": "Probe",
    # --- R2L ---
    "ftp_write": "R2L", "guess_passwd": "R2L", "imap": "R2L", "multihop": "R2L",
    "phf": "R2L", "spy": "R2L", "warezclient": "R2L", "warezmaster": "R2L",
    "sendmail": "R2L", "named": "R2L", "snmpgetattack": "R2L", "snmpguess": "R2L",
    "xlock": "R2L", "xsnoop": "R2L", "worm": "R2L",
    # --- U2R ---
    "buffer_overflow": "U2R", "loadmodule": "U2R", "perl": "U2R", "rootkit": "U2R",
    "httptunnel": "U2R", "ps": "U2R", "sqlattack": "U2R", "xterm": "U2R",
}
FAMILIES = ["Normal", "DoS", "Probe", "R2L", "U2R"]

# The 17 attack types that appear ONLY in KDDTest+ (verified empirically in this repo).
# These constitute the built-in zero-day benchmark.
NOVEL_ATTACKS = [
    "apache2", "httptunnel", "mailbomb", "mscan", "named", "processtable", "ps", "saint",
    "sendmail", "snmpgetattack", "snmpguess", "sqlattack", "udpstorm", "worm", "xlock",
    "xsnoop", "xterm",
]
