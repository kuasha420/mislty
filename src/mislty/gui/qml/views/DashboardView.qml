import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    function formatUptime(seconds) {
        if (!seconds || seconds <= 0) return "0 h 00m";
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        return h + " h " + (m < 10 ? "0" + m : m) + "m";
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        rightPadding: 16
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: scroll.availableWidth
            spacing: Theme.spacingLg

            // ===============================================================
            // 2x2 BALANCED QUAD-CARD GRID (MATCHING CONCEPT MOCKUP)
            // ===============================================================
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: Theme.spacingLg
                columnSpacing: Theme.spacingLg

                // -----------------------------------------------------------
                // CARD 1 (TOP-LEFT): CONNECTION STATUS
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 240
                    Layout.minimumHeight: 230
                    title: "Connection Status"
                    subtitle: {
                        if (!(bridge?.modemPresent ?? false)) return "Modem Hardware Offline";
                        if (bridge?.connected ?? false) {
                            var op = (bridge?.operator && bridge.operator.length > 0) ? bridge.operator : "Cellular Network";
                            var tech = (bridge?.technology && bridge.technology.length > 0) ? bridge.technology : "4G LTE";
                            return op + " • " + tech;
                        }
                        return "Cellular Standby • Ready to Dial";
                    }
                    iconName: (bridge?.connected ?? false) ? "zap" : "power"
                    iconColor: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.textMuted

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingMd

                        Item { Layout.fillHeight: true }

                        // 3-State Gradient Action Button (Matching Concept Artwork)
                        FelineButton {
                            id: dataActionBtn
                            Layout.fillWidth: true
                            implicitHeight: 46
                            buttonRadius: Theme.radiusPill
                            variant: {
                                if (!(bridge?.modemPresent ?? false)) return "secondary";
                                if (bridge?.connected ?? false) return "danger";
                                return "primary";
                            }
                            text: {
                                if (!(bridge?.modemPresent ?? false)) return "Modem Offline";
                                if (bridge?.connecting ?? false) return "Connecting (ppp0)...";
                                if (bridge?.connected ?? false) return "Disconnect Data";
                                return "Connect Data";
                            }
                            loading: bridge?.connecting ?? false
                            loadingText: "Connecting (ppp0)..."
                            iconName: {
                                if (!(bridge?.modemPresent ?? false)) return "plug";
                                if (bridge?.connected ?? false) return "square";
                                return "zap";
                            }
                            disabled: !(bridge?.modemPresent ?? false) || (bridge?.connecting ?? false)
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    if (bridge.connected) {
                                        bridge.disconnectData();
                                    } else {
                                        bridge.connectData("internet");
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        // Primary Telemetry Row: Uptime and IP Address
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXl

                            // Uptime Column
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    text: "Uptime"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeCaption
                                    color: Theme.textMuted
                                }

                                Text {
                                    text: {
                                        if (!(bridge?.connected ?? false)) return "0 h 00m";
                                        return root.formatUptime(bridge?.sessionDuration ?? 0);
                                    }
                                    font.family: Theme.fontSans
                                    font.pixelSize: 15
                                    font.weight: Font.Medium
                                    color: Theme.textPrimary
                                }
                            }

                            // IP Address Column
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    text: "IP Address"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeCaption
                                    color: Theme.textMuted
                                }

                                Text {
                                    text: {
                                        if (!(bridge?.connected ?? false)) return "—";
                                        if (bridge?.ipAddress && bridge.ipAddress.length > 0) return bridge.ipAddress;
                                        return "—";
                                    }
                                    font.family: Theme.fontSans
                                    font.pixelSize: 15
                                    font.weight: Font.Medium
                                    color: Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        // Divider
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.colorBorder
                            opacity: 0.6
                        }

                        // Secondary Telemetry Row: Total Transfer & DNS Servers
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXl

                            // Total Data Transferred
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    text: "Total Data:"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeCaption
                                    color: Theme.textMuted
                                }

                                Text {
                                    text: Theme.formatBytes(bridge?.totalBytesTransferred ?? 0)
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeCaption
                                    font.weight: Font.DemiBold
                                    color: Theme.colorCyan
                                }
                            }

                            // WAN Interface & DNS
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    text: "DNS:"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeCaption
                                    color: Theme.textMuted
                                }

                                Text {
                                    text: (bridge?.connected ?? false) ? (bridge?.dnsServersFormatted || "Auto Assigned") : "—"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeCaption
                                    color: Theme.textSecondary
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }

                // -----------------------------------------------------------
                // CARD 2 (TOP-RIGHT): LIVE DUAL BANDWIDTH MONITOR
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 240
                    Layout.minimumHeight: 230
                    title: "Live Dual Bandwidth Monitor"
                    subtitle: "Real-time PPP/Cellular Throughput"
                    iconName: "activity"
                    iconColor: Theme.colorCyan

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingSm

                        // Subtitle / Legend Row (matching concept artwork)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingMd

                            RowLayout {
                                spacing: 6
                                Rectangle {
                                    width: 6
                                    height: 6
                                    radius: 3
                                    color: "#38bdf8"
                                }
                                Text {
                                    text: "DL: " + Theme.formatRate(bridge?.rxRate ?? 0)
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: "#38bdf8"
                                    font.weight: Font.Medium
                                }
                            }

                            RowLayout {
                                spacing: 6
                                Rectangle {
                                    width: 6
                                    height: 6
                                    radius: 3
                                    color: "#f59e0b"
                                }
                                Text {
                                    text: "UL: " + Theme.formatRate(bridge?.txRate ?? 0)
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: "#f59e0b"
                                    font.weight: Font.Medium
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Cumulative DL/UL summary
                            Text {
                                text: "DL: " + Theme.formatBytes(bridge?.rxBytes ?? 0) + " • UL: " + Theme.formatBytes(bridge?.txBytes ?? 0)
                                font.family: Theme.fontMono
                                font.pixelSize: 10
                                color: Theme.textMuted
                            }
                        }

                        // Smooth Dual Spline Wave Graph
                        DualWaveGraph {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            rxRate: bridge?.rxRate ?? 0
                            txRate: bridge?.txRate ?? 0
                            rxHistory: bridge?.trafficHistoryRx ?? []
                            txHistory: bridge?.trafficHistoryTx ?? []
                        }
                    }
                }

                // -----------------------------------------------------------
                // CARD 3 (BOTTOM-LEFT): RF TELEMETRY
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 240
                    Layout.minimumHeight: 230
                    title: "RF Telemetry"
                    subtitle: (bridge?.bandName && bridge.bandName !== "No Band") ? ("Carrier Frequency: " + bridge.bandName) : "Radio Frequency Signal Analysis"
                    iconName: "radio"
                    iconColor: Theme.colorCyan

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingXl

                        // Left: Clean Modern Mobile Tower Bars Visualizer
                        RfTowerMeter {
                            Layout.preferredWidth: 125
                            Layout.fillHeight: true
                        }

                        // Right: Clean Tabular RF Metrics (crisp white values matching concept)
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: Theme.spacingSm

                            // RSRP Row
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "RSRP"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textMuted
                                    font.weight: Font.Normal
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: (bridge?.rsrp && bridge.rsrp !== "—") ? bridge.rsrp.replace(" dBm", " dB") : "—"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Medium
                                    color: Theme.textPrimary
                                }
                            }

                            // RSRQ Row
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "RSRQ"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textMuted
                                    font.weight: Font.Normal
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: (bridge?.rsrq && bridge.rsrq !== "—") ? bridge.rsrq : "—"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Medium
                                    color: Theme.textPrimary
                                }
                            }

                            // RSSI Row
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "RSSI"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textMuted
                                    font.weight: Font.Normal
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: (bridge?.rssi && bridge.rssi !== "—") ? bridge.rssi.replace(" dBm", " dB") : "—"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Medium
                                    color: Theme.textPrimary
                                }
                            }

                            // SINR Row
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "SINR"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textMuted
                                    font.weight: Font.Normal
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: (bridge?.sinr && bridge.sinr !== "—") ? bridge.sinr : "—"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Medium
                                    color: Theme.textPrimary
                                }
                            }
                        }
                    }
                }

                // -----------------------------------------------------------
                // CARD 4 (BOTTOM-RIGHT): WI-FI CO-PROCESSOR STATUS
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 240
                    Layout.minimumHeight: 230
                    title: "Wi-Fi Co-processor Status"
                    subtitle: "Broadcom BCM43143 Subsystem"
                    iconName: "wifi"
                    iconColor: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.textMuted

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingMd

                        // Row 1: Status + Quick Toggle
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingMd

                            Icon {
                                name: "wifi"
                                size: 16
                                color: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.textMuted
                            }

                            Text {
                                text: "Status"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textSecondary
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: (bridge?.wifiPower ?? false) ? "Active" : "Offline"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Medium
                                color: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.colorDanger
                            }

                            FelineButton {
                                text: (bridge?.wifiPower ?? false) ? "Disable" : "Enable"
                                variant: (bridge?.wifiPower ?? false) ? "secondary" : "primary"
                                iconName: "power"
                                implicitHeight: 28
                                implicitWidth: 84
                                loading: bridge?.isTogglingWifi ?? false
                                loadingText: "..."
                                disabled: !(bridge?.modemPresent ?? true) || (bridge?.isTogglingWifi ?? false)
                                onClicked: {
                                    if (typeof bridge !== "undefined" && bridge) {
                                        bridge.toggleWifi();
                                    }
                                }
                            }
                        }

                        // Hairline Divider
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.colorBorder
                        }

                        // Row 2: SSID
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingMd

                            Icon {
                                name: "radio"
                                size: 16
                                color: Theme.textMuted
                            }

                            Text {
                                text: "SSID"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textSecondary
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: {
                                    if (bridge?.wifiSsid && bridge.wifiSsid.length > 0) return bridge.wifiSsid;
                                    return (bridge?.wifiPower ?? false) ? "TypeScript 420" : "—";
                                }
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Medium
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }
                        }

                        // Hairline Divider
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.colorBorder
                        }

                        // Row 3: Connected Devices
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingMd

                            Icon {
                                name: "laptop"
                                size: 16
                                color: Theme.textMuted
                            }

                            Text {
                                text: "Connected Devices"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textSecondary
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: (bridge?.wifiClientsCount ?? 0) + " Station(s)"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Medium
                                color: Theme.textPrimary
                            }
                        }
                    }
                }
            }
        }
    }
}
