
from modules.driver_monitor import run_driver_monitor


def main():
    print("GuardianDriveAI starting...")
    print("Press Q in the webcam window to quit.")

    run_driver_monitor(camera_index=0)


if __name__ == "__main__":
    main()
