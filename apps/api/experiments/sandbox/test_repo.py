import threading
import time

from morphcloud.api import Instance, InstanceStatus, MorphCloudClient
from src.config import MORPHCLOUD_API_KEY

client = MorphCloudClient(MORPHCLOUD_API_KEY)

GIT_REPO_URL = "https://github.com/yungwenpeng/react-dashboard-example"
NAME = "react-dashboard-example"
PORT = 4200


def stream_logs(instance: Instance, session_name: str, duration: float | None = None):
    print(f"\n{'─' * 50}")
    print(f"\nAttaching to logs of session {session_name}:")

    start_time = time.time()

    with instance.ssh() as ssh:
        ssh.run(f"tmux pipe-pane -t {session_name} 'cat > /tmp/{session_name}.log'")

        last_position = 0
        while True:
            # Check for timeout/duration
            if duration is not None and time.time() - start_time > duration:
                print(f"\nStopped streaming after {duration} seconds")
                break

            # Get new content from the log file
            result = ssh.run(f"cat /tmp/{session_name}.log")
            current_output = result.stdout

            if len(current_output) > last_position:
                new_output = current_output[last_position:]
                print(new_output, end="", flush=True)
                last_position = len(current_output)

            # Allow user to interrupt with Ctrl+C
            try:
                time.sleep(0.2)
            except KeyboardInterrupt:
                print("\nStreaming interrupted")
                break

    print(f"\n{'─' * 50}")
    print("Detached from logs (process still running)")


def get_repo_instance() -> Instance:
    root_instances = client.instances.list(
        metadata={"purpose": "sandbox_root_repo", "repo_name": NAME}
    )
    if len(root_instances) == 0:
        print("No sandbox_repo with repo_name = name found")
        exit()

    if len(root_instances) > 1:
        print("Multiple sandbox_repo with repo_name = name found")
        exit()

    root_instance = root_instances[0]

    instances = client.instances.list(
        metadata={"purpose": "sandbox_user_repo", "repo_name": NAME, "branched": "true"}
    )

    paused_instances = [
        instance for instance in instances if instance.status != InstanceStatus.READY
    ]

    print(f"Found {len(paused_instances)} paused instances")
    initial_time = time.time()
    if not paused_instances:
        root_instance.resume()
        _, clones = root_instance.branch(count=2)

        instance = clones[0]

        def cleanup_instances():
            other_instance = clones[1]
            other_instance.pause()
            root_instance.pause()

            instance.set_metadata(
                {"purpose": "sandbox_user_repo", "repo_name": NAME, "branched": "true"}
            )
            other_instance.set_metadata(
                {"purpose": "sandbox_user_repo", "repo_name": NAME, "branched": "true"}
            )

        threading.Thread(target=cleanup_instances).start()
    elif len(paused_instances) == 1:
        instance = paused_instances[0]

        def create_new_instance():
            root_instance.resume()
            _, clones = root_instance.branch(count=1)
            root_instance.pause()
            new_instance = clones[0]
            new_instance.pause()
            new_instance.set_metadata(
                {"purpose": "sandbox_user_repo", "repo_name": NAME, "branched": "true"}
            )

        threading.Thread(target=create_new_instance).start()

    elif len(paused_instances) > 1:
        instance = paused_instances[0]

    initial_end_time = time.time()
    print(f"Initial setup in {initial_end_time - initial_time} seconds")

    return instance


instance = get_repo_instance()

start_time = time.time()
instance.resume()
end_time = time.time()
print(f"Resumed in {end_time - start_time} seconds")

# Get service url
service_url = instance.expose_http_service(name="react_service", port=PORT)
print(f"Service URL: {service_url}")

# Stream logs
stream_logs(instance, "react_start", duration=30)

# Pause the instance
pause_time = time.time()
instance.pause()
pause_end_time = time.time()
print(f"Paused in {pause_end_time - pause_time} seconds")

# Resume the instance
resume_time = time.time()
instance.resume()
resume_end_time = time.time()

time.sleep(30)

# stop the instance
stop_time = time.time()
instance.stop()
stop_end_time = time.time()
print(f"Stopped in {stop_end_time - stop_time} seconds")
