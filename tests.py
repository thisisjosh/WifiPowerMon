import unittest
import subprocess
import time
import datetime
from unittest.mock import patch, call, MagicMock
from wifi_monitor import parse_wifi_ssids, send_ntfy_notification


class TestWifiMonitor(unittest.TestCase):

    def test_parse_wifi_ssids(self):
        test_output = "SSID\nNJSZB\nNETGEAR32\nbaz"
        self.assertEqual(parse_wifi_ssids(test_output), ["NJSZB", "NETGEAR32", "baz"])

        test_output = "SSID\nNJSZB\n--\nbaz"
        self.assertEqual(parse_wifi_ssids(test_output), ["NJSZB", "baz"])

        test_output = "SSID\n   NJSZB    \n  NETGEAR32   \n  baz  "
        self.assertEqual(parse_wifi_ssids(test_output), ["NJSZB", "NETGEAR32", "baz"])

        test_output = "SSID\n"
        self.assertEqual(parse_wifi_ssids(test_output), [])

    @patch('subprocess.run')
    @patch('time.sleep')
    @patch('wifi_monitor.send_ntfy_notification')
    def test_main_logic(self, mock_send_ntfy, mock_sleep, mock_subprocess):
        # test setup
        SCAN_INTERVAL = 0.001 # Speed up test
        OFFLINE_THRESHOLD = 0.002
        fixed_time = datetime.datetime(2025, 1, 20, 12, 30, 15)
        mock_time = datetime.datetime(2025, 1, 20, 12, 30, 15, 1) # For testing purposes, need a time that is not the same as the fixed_time.

        def mock_subprocess_run(command, **kwargs):
           if command == ["nmcli", "--fields", "SSID", "device", "wifi"]:
              if mock_subprocess_run.call_count == 1:
                return unittest.mock.MagicMock(stdout="SSID\nNJSZB\n")
              elif mock_subprocess_run.call_count == 2:
                return unittest.mock.MagicMock(stdout="SSID\nNJSZB\nNETGEAR32")
              elif mock_subprocess_run.call_count == 3:
                return unittest.mock.MagicMock(stdout="SSID\nNETGEAR32\n")
              elif mock_subprocess_run.call_count == 4:
                time.sleep(OFFLINE_THRESHOLD + 0.001) # simulate offline time
                return unittest.mock.MagicMock(stdout="SSID\nNETGEAR32")
              elif mock_subprocess_run.call_count == 5:
                return unittest.mock.MagicMock(stdout="SSID\nNJSZB\nNETGEAR32")
              else:
                return unittest.mock.MagicMock(stdout="SSID\n")

           else:
              return unittest.mock.MagicMock() # default
        
        mock_subprocess.side_effect = mock_subprocess_run

        # run tests
        first_seen = {}
        last_seen = {}
        TARGET_SSIDS = {"NJSZB", "NETGEAR32"}

        mock_subprocess_run.call_count = 1
        first_seen, last_seen, send_calls = run_test_cycle(first_seen, last_seen, TARGET_SSIDS, SCAN_INTERVAL, OFFLINE_THRESHOLD, mock_subprocess, mock_sleep, mock_send_ntfy, mock_time)
        self.assertEqual(first_seen, {"NJSZB": mock_time})
        self.assertEqual(last_seen, {"NJSZB": mock_time})
        mock_send_ntfy.assert_not_called()

        mock_subprocess_run.call_count = 2
        first_seen, last_seen, send_calls = run_test_cycle(first_seen, last_seen, TARGET_SSIDS, SCAN_INTERVAL, OFFLINE_THRESHOLD, mock_subprocess, mock_sleep, mock_send_ntfy, mock_time)
        self.assertEqual(first_seen, {"NJSZB": mock_time, "NETGEAR32": mock_time})
        self.assertEqual(last_seen, {"NJSZB": mock_time, "NETGEAR32": mock_time})
        mock_send_ntfy.assert_not_called()

        mock_subprocess_run.call_count = 3
        first_seen, last_seen, send_calls  = run_test_cycle(first_seen, last_seen, TARGET_SSIDS, SCAN_INTERVAL, OFFLINE_THRESHOLD, mock_subprocess, mock_sleep, mock_send_ntfy, mock_time)
        self.assertEqual(first_seen, {"NJSZB": mock_time, "NETGEAR32": mock_time})
        self.assertEqual(last_seen, {"NETGEAR32": mock_time})
        mock_send_ntfy.assert_not_called()

        mock_subprocess_run.call_count = 4
        first_seen, last_seen, send_calls  = run_test_cycle(first_seen, last_seen, TARGET_SSIDS, SCAN_INTERVAL, OFFLINE_THRESHOLD, mock_subprocess, mock_sleep, mock_send_ntfy, mock_time)
        self.assertEqual(first_seen, {"NJSZB": mock_time, "NETGEAR32": mock_time})
        self.assertEqual(last_seen, {"NETGEAR32": mock_time})
        mock_send_ntfy.assert_called_with("Alert: NJSZB has been offline for 0 seconds.")

        mock_subprocess_run.call_count = 5
        first_seen, last_seen, send_calls  = run_test_cycle(first_seen, last_seen, TARGET_SSIDS, SCAN_INTERVAL, OFFLINE_THRESHOLD, mock_subprocess, mock_sleep, mock_send_ntfy, mock_time)
        self.assertEqual(first_seen, {"NJSZB": mock_time, "NETGEAR32": mock_time})
        self.assertEqual(last_seen, {"NJSZB": mock_time, "NETGEAR32": mock_time})
        mock_send_ntfy.assert_has_calls([call("Alert: NJSZB has been offline for 0 seconds."), call(f"Alert: NJSZB has come back online at {mock_time}")])

def run_test_cycle(first_seen, last_seen, TARGET_SSIDS, SCAN_INTERVAL, OFFLINE_THRESHOLD, mock_subprocess, mock_sleep, mock_send_ntfy, mock_time):
    try:
        result = mock_subprocess(["nmcli", "--fields", "SSID", "device", "wifi"], capture_output=True, text=True, check=True)
        ssids = parse_wifi_ssids(result.stdout)
        current_time = mock_time

        for ssid in ssids:
            if ssid not in first_seen:
                first_seen[ssid] = current_time
            last_seen[ssid] = current_time

        for target_ssid in TARGET_SSIDS:
            if target_ssid not in ssids:
                if target_ssid in last_seen:
                    last_seen_time = last_seen[target_ssid]
                    time_since_last_seen = (current_time - last_seen_time)
                    if time_since_last_seen.total_seconds() > OFFLINE_THRESHOLD:
                        message = f"Alert: {target_ssid} has been offline for 0 seconds."
                        send_ntfy_notification(message)
                        last_seen.pop(target_ssid) # remove to be considered as come back on line
            else:
                if target_ssid not in last_seen:
                    message = f"Alert: {target_ssid} has come back online at {current_time}"
                    send_ntfy_notification(message)

    except subprocess.CalledProcessError as e:
        print(f"Error running nmcli: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    mock_sleep(SCAN_INTERVAL)
    return first_seen, last_seen, mock_send_ntfy.mock_calls

if __name__ == "__main__":
    unittest.main(verbosity=2)