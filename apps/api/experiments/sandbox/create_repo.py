import time

from morphcloud.api import Instance, InstanceExecResponse, MorphCloudClient, Snapshot
from src.config import MORPHCLOUD_API_KEY

client = MorphCloudClient(MORPHCLOUD_API_KEY)

GIT_REPO_URL = "https://github.com/yungwenpeng/react-dashboard-example"
NAME = "react-dashboard-example"
PORT = 4200


def start_background_process(
    instance: Instance, command: str, session_name: str = "background_session"
) -> None:
    tmux_cmd: str = f"tmux new-session -d -s {session_name} '{command}'"
    result: InstanceExecResponse = instance.exec(tmux_cmd)

    if result.exit_code != 0:
        raise RuntimeError(f"Failed to start tmux session: {result.stderr}")


def stream_logs(instance: Instance, session_name: str, duration: float | None = None):
    print(f"\n{'─' * 50}")
    print(f"\nAttaching to logs of session {session_name}:")

    start_time = time.time()

    with instance.ssh() as ssh:
        ssh.run(f"tmux pipe-pane -t {session_name} 'cat > /tmp/{session_name}.log'")

        last_position = 0
        while True:
            if duration is not None and time.time() - start_time > duration:
                print(f"\nStopped streaming after {duration} seconds")
                break

            result = ssh.run(f"cat /tmp/{session_name}.log")
            current_output = result.stdout

            if len(current_output) > last_position:
                new_output = current_output[last_position:]
                print(new_output, end="", flush=True)
                last_position = len(current_output)

            try:
                time.sleep(0.2)
            except KeyboardInterrupt:
                print("\nStreaming interrupted")
                break

    print(f"\n{'─' * 50}")
    print("Detached from logs (process still running)")


def wait_til_server_running(instance: Instance, session_name: str) -> bool:
    healthy_codes: list[str] = ["200", "500", "307", "201", "301", "302", "403", "304"]

    result = instance.exec(f"tmux ls | grep {session_name}")
    if result.exit_code != 0:
        print("Tmux session not running")
        return False

    print("Session name:", session_name)
    while True:
        result = instance.exec(
            f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{PORT}"
        )
        if result.stdout in healthy_codes:
            return True
        time.sleep(1)


def get_base_sandbox_snapshot() -> Snapshot:
    base_sandbox_snapshots = client.snapshots.list(metadata={"purpose": "sandbox_base"})

    if len(base_sandbox_snapshots) == 0:
        print("No base sandbox snapshot found")
        exit()

    base_sandbox_snapshot = base_sandbox_snapshots[0]

    for snapshot in base_sandbox_snapshots:
        current_version = snapshot.metadata.get("version", "0.0.0")
        base_version = base_sandbox_snapshot.metadata.get("version", "0.0.0")

        current_parts = current_version.split(".")
        base_parts = base_version.split(".")

        is_newer = False
        for i in range(max(len(current_parts), len(base_parts))):
            current_part = int(current_parts[i]) if i < len(current_parts) else 0
            base_part = int(base_parts[i]) if i < len(base_parts) else 0

            if current_part > base_part:
                is_newer = True
                break
            elif current_part < base_part:
                break

        if is_newer:
            print(
                f"Snapshot {snapshot.id} has a higher version ({current_version}) than {base_sandbox_snapshot.id} ({base_version})"
            )
            base_sandbox_snapshot = snapshot

    print(
        f"Using base sandbox snapshot `{base_sandbox_snapshot.id}` on version {base_sandbox_snapshot.metadata['version']}"
    )

    return base_sandbox_snapshot


def create_root_repo_instance() -> Instance:
    start_time = time.time()
    instance: Instance = client.instances.start(snapshot_id=base_sandbox_snapshot.id)
    end_time = time.time()
    print(f"Instance started in {end_time - start_time} seconds")

    clone_time = time.time()
    clone_result: InstanceExecResponse = instance.exec(
        command=f"git clone {GIT_REPO_URL} /repo"
    )
    if clone_result.exit_code != 0:
        raise RuntimeError(f"Failed to clone repo: {clone_result.stderr}")
    clone_end_time = time.time()
    print(f"Cloned in {clone_end_time - clone_time} seconds")

    install_time = time.time()
    install_result: InstanceExecResponse = instance.exec(
        command="cd /repo && npm install"
    )
    if install_result.exit_code != 0:
        raise RuntimeError(f"Failed to install npm: {install_result.stderr}")
    install_end_time = time.time()
    print(f"Installed in {install_end_time - install_time} seconds")

    start_time = time.time()
    session_name = "react_start"
    start_background_process(instance, "cd /repo && npm start", session_name)
    wait_til_server_running(instance, session_name)
    end_time = time.time()
    print(f"Started npm start in {end_time - start_time} seconds")

    instances: list[Instance] = client.instances.list(
        metadata={"purpose": "sandbox_root_repo", "repo_name": NAME}
    )
    for x_instance in instances:
        print(f"Deleting instance {x_instance.id}")
        x_instance.delete()

    instance.set_metadata({"purpose": "sandbox_root_repo", "repo_name": NAME})

    pause_time = time.time()
    instance.pause()
    pause_end_time = time.time()
    print(f"Paused in {pause_end_time - pause_time} seconds")

    return instance


base_sandbox_snapshot = get_base_sandbox_snapshot()
instance = create_root_repo_instance()
