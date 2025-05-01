from morphcloud.api import MorphCloudClient
from src.config import MORPHCLOUD_API_KEY

client = MorphCloudClient(MORPHCLOUD_API_KEY)

PURPOSE = "sandbox_base"
VERSION = "0.0.9"

snapshots = client.snapshots.list(metadata={"purpose": PURPOSE, "version": VERSION})
if len(snapshots) > 0:
    print(f"Snapshot with purpose {PURPOSE} and version {VERSION} already exists")
    for snapshot in snapshots:
        print(f"{snapshot.metadata['purpose']} {snapshot.metadata['version']}")
    exit()

new_snapshot = client.snapshots.create(
    vcpus=6,
    memory=12288,  # MB
    disk_size=15000,  # MB
    digest="sandbox_test",  # Optional
)


instance = client.instances.start(snapshot_id=new_snapshot.id)

# Part 1: System packages
commands_part1 = """
apt-get update
apt-get install -y --no-install-recommends procps curl git socat lsof lz4 ripgrep psmisc tmux bsdmainutils htop nginx
"""
result_part1 = instance.exec(command=commands_part1)
print("Part 1 completed")
# print(result_part1.stdout)

# Part 2: Node.js setup
commands_part2 = """
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
npm install -g npm@latest
npm install -g corepack@latest
"""
result_part2 = instance.exec(command=commands_part2)
print("Part 2 completed")
# print(result_part2.stdout)

# Part 3: Package managers setup
commands_part3 = """
corepack enable
corepack enable pnpm
corepack enable yarn
npm install -g bun --force
npm install -g turbo --force
corepack prepare yarn@stable --activate
corepack prepare pnpm
corepack use pnpm@latest-10
yarn set version stable
rm -rf /var/lib/apt/lists/*

echo 'export NODE_OPTIONS="--max-old-space-size=8192"' >> /etc/profile
echo 'export NODE_OPTIONS="--max-old-space-size=8192"' >> /etc/bash.bashrc
echo 'export NODE_OPTIONS="--max-old-space-size=8192"' >> /root/.bashrc
"""
result_part3 = instance.exec(command=commands_part3)
print("Part 3 completed")
# print(result_part3.stdout)

# Part 4: Directory setup and NVM
commands_part4 = """
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
nvm install
mkdir -p /repo
"""
result_part4 = instance.exec(command=commands_part4)
print("Part 4 completed")
# print(result_part4.stdout)


new_snapshot = instance.snapshot(digest="sandbox_test")
new_snapshot.set_metadata({"purpose": PURPOSE, "version": VERSION})
print(new_snapshot.id)

instance.stop()
