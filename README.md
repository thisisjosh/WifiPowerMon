# WifiPowerMon

Monitors power outages by observing the availability of nearby WiFi networks.

## How is this useful?

I live in an area with frequent power outages. When the power goes out, I manually switch to a whole-house generator. I needed a way to be notified when grid power is restored so I can turn off the generator.

This script monitors the WiFi networks in my neighborhood. When networks that typically go down during an outage come back online, it sends a push notification to my phone. This tells me that power has been restored, and I can switch back to the grid.

## Requirements

This script is designed to run on a small, Linux-based single-board computer (like a Raspberry Pi) and has minimal dependencies. I run on a cheap used Orange Pi Zero that I found on eBay.

*   `nmcli` (NetworkManager command-line tool)
*   `curl` (for sending ntfy notifications)
*   Python 3

## Installation

1.  **Clone this repository.**
    ```bash
    git clone https://github.com/thisisjosh/WifiPowerMon
    ```

2.  **Configure the monitor:**
    Edit the configuration file to specify which WiFi networks to monitor and your `ntfy` topic.
    ```bash
    nano ~/WifiPowerMon/config.json
    ```
    See the [Configuration](#configuration) section below for details on the available options.

    Edit the `wifimon.service` to use the correct full paths for where the `WifiPowerMon` directory is.

3.  **Run the installer:**
    The installer will set up a systemd service to run the monitor automatically.
    ```bash
    sudo ./install.sh
    ```

## Usage

The script will be started automatically by the `systemd` service. You can check its status or view its logs using the following commands.

**Check service status:**
```bash
sudo systemctl status wifimon.service
```

**Connect to the screen session and view the service console:**
```bash
screen -r wifimon
```

**Restart the service:**
```bash
sudo systemctl restart wifimon.service
```

## Push Notifications with ntfy

This project uses [ntfy.sh](https://ntfy.sh) to send free push notifications to your phone.

**Setup:**

1.  **Install the ntfy app** on your Android or iOS device.
2.  **Create a topic.** A topic is like a channel name. It can be any string, but it's best to choose something unique and hard to guess (e.g., `elmstreet_power_alerts_a5b2c`).
3.  **Subscribe to your topic** in the app.
4.  **Update your `config.json`** with the same topic name in the `NTFY_TOPIC` field.

Now, any message sent to that topic by the `wifi_monitor.py` script will appear as a push notification on your phone.

## Configuration

The `config.json` file contains the following options:

| Key                        | Description                                                                                                                            | Default |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `TARGET_SSIDS`             | A list of WiFi SSIDs (network names) to monitor. These should be networks that you expect to go offline during a power outage.           | `[]`      |
| `NTFY_TOPIC`               | The topic name for your `ntfy.sh` push notifications.                                                                                    | `""`      |
| `SCAN_INTERVAL`            | The number of seconds to wait between scanning for WiFi networks.                                                                      | `15`    |
| `OFFLINE_THRESHOLD`        | The number of seconds a network must be unseen before it is considered "offline". This prevents false alarms from intermittent signals. | `300`   |
| `SIMULATION_TARGET_SSIDS`  | Target SSIDs to use when running in simulation mode (`--simulate`).                                                                      | `[]`      |
| `SIMULATION_NTFY_TOPIC`    | `ntfy.sh` topic to use in simulation mode.                                                                                               | `""`      |
| `SIMULATION_SCAN_INTERVAL` | Scan interval to use in simulation mode.                                                                                               | `1`     |
| `SIMULATION_OFFLINE_THRESHOLD` | Offline threshold to use in simulation mode.                                                                                         | `2`     |

## Disclaimer of Warranty and Liability

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.