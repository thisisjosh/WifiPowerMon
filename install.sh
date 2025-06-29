cp wifimon.service /etc/systemd/system/wifimon.service
systemctl daemon-reload
systemctl enable wifimon.service
systemctl start wifimon.service
systemctl status wifimon.service
