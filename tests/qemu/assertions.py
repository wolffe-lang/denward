"""Independent assertions for live facts and explicitly labelled judge replays."""
import copy
import json
from pathlib import Path

IMAGE = '6297bcdfacbea88505c78456a52a008d02a7253e3853c5d70a2dba87ca582b0f'
HASH = 'f6dd7fec8584ad00219a447071c1fa368a1caee4d9c146083d233713ddccd2c0'
ROWS = {
    'P01-image': {'image_sha256': IMAGE},
    'P02-usb-ext2': {'bytes': 3145728, 'reference_sha256': HASH, 'usb_ext2_errno': 0, 'usb_ext2_sha256': HASH},
    'P03-virtio-ext3': {'virtio_ext3_errno': 0, 'virtio_ext3_sha256': HASH},
    'P04-independent-filesystems': {'ext2_fsck_exit': 0, 'ext3_fsck_exit': 0},
    'P05-ssh-send': {'ssh_send_exit': 0, 'ssh_receiver_sha256': HASH},
    'P06-ssh-fetch': {'ssh_fetch_exit': 0, 'ssh_returned_sha256': HASH},
    'P07-fat-unsupported': {'vfat_errno': 19, 'fat_errno': 19},
    'P08-usb-reconnect-unsupported': {'unmount_errno': 0, 'replug_qmp_success': True, 'replug_errno': 2, 'new_disk_exposed': False},
    'P09-utility-capabilities': {'mount_utility': False, 'etc_fstab': False, 'bare_sync_utility_supported': False},
    'P10-du-status': {'du_exit': 0},
}


def verdicts(facts):
    result = {}
    for name, expected in ROWS.items():
        result[name] = all(k in facts and type(facts[k]) is type(v) and facts[k] == v for k, v in expected.items())
    known = {k for expected in ROWS.values() for k in expected}
    result['P11-exact-facts'] = set(facts) == known
    return result


def self_test(facts):
    if not all(verdicts(facts).values()):
        return False
    for name, expected in ROWS.items():
        for key, value in expected.items():
            changed = copy.deepcopy(facts)
            changed[key] = not value if type(value) is bool else (value + 1 if type(value) is int else 'wrong')
            if verdicts(changed)[name]:
                return False
            del changed[key]
            if verdicts(changed)[name]:
                return False
    changed = dict(facts, unexpected=True)
    return not verdicts(changed)['P11-exact-facts']


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('facts', type=Path)
    ap.add_argument('--mode', choices=['judge-replay', 'live-qemu'], required=True)
    a = ap.parse_args()
    facts = json.loads(a.facts.read_text())
    ok = True
    for name, good in verdicts(facts).items():
        print(('PASS' if good else 'FAIL') + ' ' + name + ' mode=' + a.mode)
        ok = ok and good
    test = self_test(facts)
    print(('PASS' if test else 'FAIL') + ' P12-judge-mutations')
    return int(not (ok and test))


if __name__ == '__main__':
    raise SystemExit(main())
