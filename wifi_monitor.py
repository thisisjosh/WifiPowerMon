#!/usr/bin/env python3

import subprocess
import time
import datetime
import argparse
import logging
import json

SIMULATION_START_TIME = None
SIMULATION_ENDED = False
FIRST_SCAN_DONE = False  # Flag to check if the first scan has been completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_config(config_file='/home/josh/WifiPowerMon/config.json'):
    """Loads configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_file}")
        exit(1)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in configuration file: {config_file}")
        exit(1)


def parse_wifi_ssids(nmcli_output):
    """Parses the SSID column from nmcli output when using --fields SSID."""
    ssids = []
    lines = nmcli_output.strip().split("\n")
    # Skip the header line
    for line in lines[1:]:
        ssid = line.strip()  # Remove any trailing whitespace
        if ssid and ssid != "--":  # ignore blank lines and hidden ssids
            ssids.append(ssid)
    return ssids

def format_duration(seconds):
    """Convert seconds into a friendly string of hours, minutes, and seconds."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

def send_ntfy_notification(message, topic, simulate=False):
    """Sends a notification to ntfy.sh using curl."""
    logging.info(f"🔔{topic} {message}")
    if simulate and len(topic) == 0:
        return
    try:
        subprocess.run(
            ["/usr/bin/curl", "-d", message, f"https://ntfy.sh/{topic}"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Error sending ntfy notification with curl: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


def simulate_nmcli_output(target_ssids):
    """Simulates nmcli output with predictable patterns based on time."""
    global SIMULATION_START_TIME, SIMULATION_ENDED

    if SIMULATION_START_TIME is None:
        SIMULATION_START_TIME = datetime.datetime.now()

    elapsed_time = (datetime.datetime.now() - SIMULATION_START_TIME).total_seconds()
    fake_ssids = ["FOO", "BAR", "BLAH"]
    output = "SSID\n"

    # Simulation logic with comments for clarity
    if elapsed_time < 5:  # First 5 seconds: All SSIDs present
        output += "\n".join(fake_ssids + list(target_ssids))
        logging.info("Simulation: All SSIDs online.")
    elif elapsed_time < 10:  # Second 5 seconds: Target SSIDs disappear
        output += "\n".join(fake_ssids)
        logging.info("Simulation: Target SSIDs offline.")
    elif elapsed_time < 15:  # Third 5 seconds: One target SSID comes back
        output += "\n".join(fake_ssids + [list(target_ssids)[0]])
        logging.info("Simulation: One target SSID back online.")
    elif elapsed_time < 20:  # Fourth 5 seconds: Both target SSIDs come back
        output += "\n".join(fake_ssids + list(target_ssids))
        logging.info("Simulation: All target SSIDs back online.")
    else:
        if not SIMULATION_ENDED:
            logging.info("Simulation finished. 🏁")
            SIMULATION_ENDED = True
        return None  # Signal to the main loop to break

    return output


def main():
    parser = argparse.ArgumentParser(description="Monitor wifi networks and send ntfy.sh notifications.")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode using fake nmcli output.")
    parser.add_argument("--targets", nargs='+', help="List of target SSIDs to monitor", required=False)  # Targets can come from command line or config
    parser.add_argument("--debug", action="store_true", help="Set the log level to debug")
    args = parser.parse_args()

    config = load_config()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    global FIRST_SCAN_DONE
    first_seen = {}  # Key: SSID, Value: datetime when first seen
    last_seen = {}  # Key: SSID, Value: datetime when last seen
    target_states = {}  # Key: SSID, Value: "online" or "offline"
    target_offline_times = {}  # Key: SSID, Value: datetime when target went offline

    # Read in targets. Command line target takes precedence
    if args.simulate:
        if args.targets:
            TARGET_SSIDS = set(args.targets)
        else:
            TARGET_SSIDS = set(config.get('SIMULATION_TARGET_SSIDS', []))
            if not TARGET_SSIDS:
                logging.error("No simulation target SSIDs provided in command line or config file.")
                exit(1)
    else:
        if args.targets:
            TARGET_SSIDS = set(args.targets)
        else:
            TARGET_SSIDS = set(config.get('TARGET_SSIDS', []))
            if not TARGET_SSIDS:
                logging.error("No target SSIDs provided in command line or config file.")
                exit(1)

    SCAN_INTERVAL = config.get("SCAN_INTERVAL", 15)
    OFFLINE_THRESHOLD = config.get("OFFLINE_THRESHOLD", 300)
    NTFY_TOPIC = config.get("NTFY_TOPIC", "my_wifi_monitor")

    simulate = args.simulate

    if simulate:
        SCAN_INTERVAL = config.get("SIMULATION_SCAN_INTERVAL", 1)
        OFFLINE_THRESHOLD = config.get("SIMULATION_OFFLINE_THRESHOLD", 3)
        NTFY_TOPIC = config.get("SIMULATION_NTFY_TOPIC", "my_wifi_monitor")
    
    send_ntfy_notification("Wifi Monitor started. 🚀", NTFY_TOPIC, simulate)

    while True:
        if simulate:
            result_text = simulate_nmcli_output(TARGET_SSIDS)
            if result_text is None:  # simulation is complete
                break
        else:
            try:
                result = subprocess.run(["nmcli", "--fields", "SSID", "device", "wifi"], capture_output=True, text=True, check=True)
                result_text = result.stdout
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running nmcli: {e}")
                time.sleep(SCAN_INTERVAL)
                continue
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")
                time.sleep(SCAN_INTERVAL)
                continue

        ssids = parse_wifi_ssids(result_text)
        current_time = datetime.datetime.now()
        logging.debug(f"SSIDs detected: {ssids} at {current_time}")

        for ssid in ssids:
            if ssid not in first_seen:
                first_seen[ssid] = current_time
                logging.info(f"First seen: {ssid} at {current_time} 👀")
            last_seen[ssid] = current_time  # Update last seen for all detected SSIDs

        for target_ssid in TARGET_SSIDS:
            if target_ssid not in ssids:  # Target not found in current scan
                if target_ssid in last_seen:  # Was previously seen
                    time_since_last_seen = (current_time - last_seen[target_ssid]).total_seconds()
                    if time_since_last_seen > OFFLINE_THRESHOLD and target_states.get(target_ssid) != "offline":
                        message = f"📴 {target_ssid} is offline"
                        send_ntfy_notification(message, NTFY_TOPIC, simulate)
                        target_states[target_ssid] = "offline"
                        target_offline_times[target_ssid] = current_time
            else:  # target is in current scan
                if not FIRST_SCAN_DONE:  # Do not send notifications during the first scan.
                    if target_ssid not in target_states:
                        target_states[target_ssid] = "online"
                elif target_ssid not in target_states or target_states[target_ssid] == "offline":  # if target is not in target states or it's been reported as offline
                    if target_ssid in target_offline_times:
                        time_offline = (current_time - target_offline_times[target_ssid]).total_seconds()
                    else:
                        time_offline = 0
                    time_offline_message = format_duration(time_offline)
                    message = f"📡 {target_ssid} is back after {time_offline_message} of downtime"
                    send_ntfy_notification(message, NTFY_TOPIC, simulate)
                    target_states[target_ssid] = "online"
        FIRST_SCAN_DONE = True
        logging.debug(f"Target States: {target_states}")
        time.sleep(SCAN_INTERVAL)
    if simulate:
        print("Simulation completed.")

if __name__ == "__main__":
    main()