#!/usr/bin/env python3
"""Assert the pinned ISO's storage capabilities in an isolated throwaway runner."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import select
import shutil
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
JUDGE = runpy.run_path(str(ROOT / 'tests/qemu/assertions.py'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while b := f.read(131072):
            h.update(b)
    return h.hexdigest()


def execute(args, **kw):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', type=Path, required=True)
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--preflight', action='store_true')
    a = ap.parse_args()
    if not (Path('/.dockerenv').exists() or Path('/run/.containerenv').exists()) or {n for _, n in socket.if_nameindex()} != {'lo'}:
        raise RuntimeError('isolated container with loopback-only network required')
    if os.geteuid() != 0:
        raise RuntimeError('fixture sshd requires container root')
    for name in ['gcc', 'ssh-keygen', 'sshd', 'mke2fs', 'mkfs.fat', 'e2fsck', 'debugfs', 'qemu-system-x86_64']:
        if not shutil.which(name):
            raise RuntimeError('missing probe dependency')
    if digest(a.image) != JUDGE['IMAGE']:
        raise RuntimeError('test ISO digest mismatch')
    p = a.workspace.resolve()
    if not re.fullmatch(r'[/A-Za-z0-9_.-]+', str(p)) or len(str(p / 'qmp.sock').encode()) > 100:
        raise RuntimeError('probe workspace needs a short shell-safe absolute path')
    if p.exists():
        raise RuntimeError('probe workspace must be new')
    if not os.access('/dev/kvm', os.R_OK | os.W_OK):
        raise RuntimeError('KVM device unavailable')
    if a.preflight:
        print('PASS P00-preflight only; no QEMU result claimed', flush=True)
        return 0
    p.mkdir(parents=True, mode=0o700, exist_ok=False)
    (p / 'scratch').mkdir()
    os.environ['TMPDIR'] = str(p / 'scratch')
    seed = p / 'seed'
    seed.mkdir(mode=0o700)
    execute(['gcc', '-nostdlib', '-static', '-s', '-Wl,--build-id=none', str(ROOT / 'tests/qemu/mountprobe.S'), '-o', str(p / 'mountprobe')])
    for key in [seed / 'client_key', p / 'host_key']:
        execute(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'fixture', '-f', str(key)])
    (seed / 'known_hosts').write_text('[10.0.2.2]:24132 ' + (p / 'host_key.pub').read_text())
    (seed / 'probe.bin').write_bytes(bytes(range(256)) * 12288)
    for kind in ['ext2', 'ext3', 'fat']:
        image = p / (kind + '.img')
        with image.open('xb') as f:
            f.truncate(96 * 1024 * 1024)
        if kind == 'fat':
            execute(['mkfs.fat', '-F', '32', str(image)])
        else:
            execute(['mke2fs', '-q', '-F', '-t', kind, '-b', '4096', '-d', str(seed), str(image)])
    (p / 'sshd_config').write_text(f'Port 24132\nListenAddress 127.0.0.1\nHostKey {p}/host_key\nPidFile {p}/sshd.pid\nAuthorizedKeysFile {seed}/client_key.pub\nStrictModes no\nPermitRootLogin yes\nPasswordAuthentication no\nUsePAM no\nLogLevel VERBOSE\n')
    Path('/run/sshd').mkdir(exist_ok=True)
    serial = (p / 'serial.log').open('wb')
    ssh_log = (p / 'sshd.log').open('wb')
    sshd = subprocess.Popen([shutil.which('sshd'), '-D', '-e', '-f', str(p / 'sshd_config')], stdout=ssh_log, stderr=ssh_log)
    qemu = None
    try:
        args = ['qemu-system-x86_64', '-machine', 'q35', '-accel', 'kvm', '-cpu', 'max', '-smp', '2', '-m', '2048', '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-no-reboot', '-cdrom', str(a.image.resolve()), '-boot', 'd', '-netdev', 'user,id=n0', '-device', 'virtio-net-pci,netdev=n0', '-device', 'qemu-xhci,id=xhci', '-qmp', 'unix:' + str(p / 'qmp.sock') + ',server=on,wait=off']
        for index, kind in enumerate(['ext2', 'ext3', 'fat']):
            args += ['-drive', f'file={p}/{kind}.img,if=none,id=d{index},format=raw', '-device', f'usb-storage,drive=d{index},bus=xhci.0,id=usbprobe' if kind == 'ext2' else f'virtio-blk-pci,drive=d{index}']
        qemu = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        (p / 'qemu.pid').write_text(str(qemu.pid) + '\n')
        output = bytearray()

        def wait(marker, timeout=120):
            start = len(output)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if marker in output[start:]:
                    return bytes(output[start:]).decode('utf-8', 'replace').replace('\r', '')
                if select.select([qemu.stdout], [], [], 1)[0]:
                    b = os.read(qemu.stdout.fileno(), 65536)
                    if not b:
                        raise RuntimeError('QEMU ended before expected marker')
                    output.extend(b)
                    serial.write(b)
                    serial.flush()
            raise TimeoutError('guest command deadline')

        def guest(command, tag):
            qemu.stdin.write((command + '; printf "\\nDENWARD_' + tag + '_END\\n"\n').encode())
            qemu.stdin.flush()
            return wait(('DENWARD_' + tag + '_END\r\n').encode())

        def status(text, key):
            m = re.search(r'(?m)^' + re.escape(key) + r'=([0-9]+)$', text)
            if not m:
                raise RuntimeError('guest status missing')
            return int(m[1])

        def file_hash(text, path):
            m = re.search(r'(?m)^([0-9a-f]{64})  ' + re.escape(path) + r'$', text)
            return m[1] if m else ''

        wait(b'$ ')
        capabilities = guest('command -v mount >/dev/null; printf "mount_status=%s\\n" "$?"; test -f /etc/fstab; printf "fstab_status=%s\\n" "$?"; sync >/dev/null 2>&1; printf "sync_status=%s\\n" "$?"', 'CAPS')
        encoded = base64.b64encode((p / 'mountprobe').read_bytes()).decode()
        qemu.stdin.write(b"base64 -d > /mountprobe <<'PROBE_EOF'\n")
        qemu.stdin.flush()
        time.sleep(.1)
        for at in range(0, len(encoded), 76):
            qemu.stdin.write((encoded[at:at + 76] + '\n').encode())
            qemu.stdin.flush()
            time.sleep(.02)
        qemu.stdin.write(b'PROBE_EOF\n')
        qemu.stdin.flush()
        time.sleep(.3)
        mounts = guest('chmod 700 /mountprobe; mkdir -p /mnt/e2 /mnt/e3 /mnt/fat; /mountprobe /dev/sda /mnt/e2 ext2; printf "e2=%s\\n" "$?"; /mountprobe /dev/vda /mnt/e3 ext3; printf "e3=%s\\n" "$?"; /mountprobe /dev/vdb /mnt/fat vfat; printf "vfat=%s\\n" "$?"; /mountprobe /dev/vdb /mnt/fat fat; printf "fat=%s\\n" "$?"', 'MOUNT')
        written = guest('cp /mnt/e2/probe.bin /mnt/e2/copied.bin; cp /mnt/e2/probe.bin /mnt/e3/copied.bin; sha256sum /mnt/e2/copied.bin /mnt/e3/copied.bin; /mountprobe sync', 'WRITE')
        ssh = 'ssh -T -p 24132 -i /mnt/e2/client_key -o UserKnownHostsFile=/mnt/e2/known_hosts root@10.0.2.2'
        sent = guest(ssh + " 'cat > " + str(p) + "/remote.bin' < /mnt/e2/probe.bin; printf 'sent=%s\\n' \"$?\"", 'SEND')
        fetched = guest(ssh + " 'cat " + str(p) + "/remote.bin' > /mnt/e3/returned.bin; printf 'fetched=%s\\n' \"$?\"; sha256sum /mnt/e3/returned.bin", 'FETCH')
        unmounted = guest('du -skx / >/dev/null; printf "du=%s\\n" "$?"; /mountprobe umount /mnt/e2; printf "unmount=%s\\n" "$?"', 'UNMOUNT')
        c = socket.socket(socket.AF_UNIX)
        c.connect(str(p / 'qmp.sock'))
        with c, c.makefile('rwb', buffering=0) as qmp_io:
            json.loads(qmp_io.readline())

            def qmp(name, arguments=None):
                qmp_io.write((json.dumps({'execute': name, 'arguments': arguments or {}}) + '\n').encode())
                while True:
                    row = json.loads(qmp_io.readline())
                    if 'error' in row:
                        raise RuntimeError('QMP command failed')
                    if 'return' in row:
                        return

            qmp('qmp_capabilities')
            qmp('device_del', {'id': 'usbprobe'})
            time.sleep(2)
            qmp('blockdev-add', {'driver': 'file', 'node-name': 'replugfile', 'filename': str(p / 'ext2.img')})
            qmp('blockdev-add', {'driver': 'raw', 'node-name': 'replugraw', 'file': 'replugfile'})
            qmp('device_add', {'driver': 'usb-storage', 'drive': 'replugraw', 'bus': 'xhci.0', 'id': 'usbprobe2'})
        time.sleep(3)
        replug = guest('test -b /dev/sdb; printf "new_disk=%s\\n" "$?"; /mountprobe /dev/sdb /mnt/e2 ext2; printf "replug=%s\\n" "$?"; /mountprobe sync', 'REPLUG')
        qemu.stdin.write(b'poweroff\n')
        qemu.stdin.flush()
        qemu.wait(timeout=30)
    finally:
        for child in [qemu, sshd]:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
        serial.close()
        ssh_log.close()
    facts = {'image_sha256': digest(a.image), 'bytes': (seed / 'probe.bin').stat().st_size, 'reference_sha256': digest(seed / 'probe.bin'), 'usb_ext2_errno': status(mounts, 'e2'), 'virtio_ext3_errno': status(mounts, 'e3'), 'usb_ext2_sha256': file_hash(written, '/mnt/e2/copied.bin'), 'virtio_ext3_sha256': file_hash(written, '/mnt/e3/copied.bin'), 'ssh_send_exit': status(sent, 'sent'), 'ssh_fetch_exit': status(fetched, 'fetched'), 'ssh_receiver_sha256': digest(p / 'remote.bin') if (p / 'remote.bin').is_file() else '', 'ssh_returned_sha256': file_hash(fetched, '/mnt/e3/returned.bin'), 'vfat_errno': status(mounts, 'vfat'), 'fat_errno': status(mounts, 'fat'), 'unmount_errno': status(unmounted, 'unmount'), 'replug_qmp_success': True, 'replug_errno': status(replug, 'replug'), 'new_disk_exposed': status(replug, 'new_disk') == 0, 'mount_utility': status(capabilities, 'mount_status') == 0, 'etc_fstab': status(capabilities, 'fstab_status') == 0, 'bare_sync_utility_supported': status(capabilities, 'sync_status') == 0, 'du_exit': status(unmounted, 'du')}
    for kind, key in [('ext2', 'usb_ext2_sha256'), ('ext3', 'virtio_ext3_sha256')]:
        fsck = subprocess.run(['e2fsck', '-fn', str(p / (kind + '.img'))], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        facts[kind + '_fsck_exit'] = fsck.returncode
        readback = execute(['debugfs', '-R', 'cat /copied.bin', str(p / (kind + '.img'))]).stdout
        if hashlib.sha256(readback).hexdigest() != facts[key]:
            facts[key] = 'independent-readback-mismatch'
    (p / 'facts.json').write_text(json.dumps(facts, indent=2) + '\n')
    failed = False
    for name, ok in JUDGE['verdicts'](facts).items():
        print(('PASS' if ok else 'FAIL') + ' ' + name + ' mode=live-qemu', flush=True)
        failed = failed or not ok
    return int(failed)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as e:
        print('FAIL P00-probe-execution ' + type(e).__name__, flush=True)
        raise SystemExit(1)
