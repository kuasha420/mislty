import QtQuick
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingXl
        spacing: Theme.spacingLg

        // --- Top Status & Quick Action Hero Banner ---
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 100
            radius: Theme.radiusLg
            color: Theme.colorObsidian
            border.color: (bridge?.connected ?? false) ? Theme.colorBorderActive : Theme.colorBorder
            border.width: (bridge?.connected ?? false) ? 1.5 : 1

            Behavior on border.color { ColorAnimation { duration: Theme.animNormal } }

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingLg
                spacing: Theme.spacingXl

                // Connection indicator icon/state
                Rectangle {
                    width: 52
                    height: 52
                    radius: Theme.radiusMd
                    color: (bridge?.connected ?? false) ? Qt.rgba(0, 240, 255, 0.12) : Qt.rgba(255, 51, 102, 0.12)
                    border.color: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.colorDanger
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: (bridge?.connected ?? false) ? "⚡" : "✕"
                        font.pixelSize: 24
                        color: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.colorDanger
                    }
                }

                // Operator & Connection State
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    RowLayout {
                        spacing: Theme.spacingSm
                        Text {
                            text: (bridge?.operator && bridge.operator.length > 0) ? bridge.operator : "Searching Carrier..."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeH2
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }
                        Rectangle {
                            height: 18
                            width: techText.implicitWidth + 10
                            radius: Theme.radiusSm
                            color: Qt.rgba(243, 156, 18, 0.15)
                            border.color: Theme.colorGold
                            border.width: 1
                            Text {
                                id: techText
                                anchors.centerIn: parent
                                text: (bridge?.technology && bridge.technology.length > 0) ? bridge.technology : "4G LTE"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                font.weight: Font.Bold
                                color: Theme.colorGold
                            }
                        }
                    }

                    Text {
                        text: {
                            if (bridge?.connecting ?? false) return "Connecting cellular data session (ppp0)...";
                            if (bridge?.connected ?? false) return "Active data session connected • IP: " + ((bridge?.ipAddress && bridge.ipAddress.length > 0) ? bridge.ipAddress : "10.64.x.x");
                            return "Cellular radio registered • Ready to connect";
                        }
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeCaption
                        color: (bridge?.connected ?? false) ? Theme.colorSuccess : Theme.textSecondary
                    }
                }

                // Primary Connect/Disconnect Action Button
                FelineButton {
                    text: {
                        if (bridge?.connecting ?? false) return "Connecting...";
                        if (bridge?.connected ?? false) return "Disconnect";
                        return "Connect Cellular";
                    }
                    variant: (bridge?.connected ?? false) ? "danger" : "primary"
                    iconGlyph: (bridge?.connected ?? false) ? "⏹" : "▶"
                    loading: bridge?.connecting ?? false
                    implicitWidth: 160
                    implicitHeight: 44
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
            }
        }

        // --- Middle Grid: Gauges and Telemetry Cards ---
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: Theme.spacingLg
            columnSpacing: Theme.spacingLg

            // 1. Cellular Signal & RF Card
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Cellular Signal & RF Quality"
                subtitle: "Qualcomm MDM9600 Primary Transceiver"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        SignalBars {
                            bars: bridge?.signalBars ?? 0
                            csq: bridge?.signalCsq ?? 0
                            dbm: bridge?.signalDbm ?? -113
                            showText: false
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: (bridge?.signalBars ?? 0) + " of 5 Signal Bars"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeH3
                                font.weight: Font.Bold
                                color: Theme.signalColor(bridge?.signalCsq ?? 0)
                            }
                            Text {
                                text: Theme.csqToDbm(bridge?.signalCsq ?? 0) + " (" + (bridge?.signalCsq ?? 0) + "/31 CSQ)"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeCaption
                                color: Theme.textSecondary
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.colorBorder
                    }

                    // Stats Grid
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "SESSION TIME"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                            Text {
                                text: Theme.durationString(bridge?.sessionDuration ?? 0)
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "IP ADDRESS"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                            Text {
                                text: (bridge?.ipAddress && bridge.ipAddress.length > 0) ? bridge.ipAddress : "—"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Bold
                                color: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.textSecondary
                            }
                        }
                    }
                }
            }

            // 2. Live Throughput & Data Meter Card
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Live Throughput & Data Meter"
                subtitle: "Real-time bandwidth pulse and cumulative transfer"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingMd

                    // Download / Upload Rate row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingXl

                        // Download rate
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            RowLayout {
                                spacing: 4
                                Text { text: "↓"; font.pixelSize: Theme.fontSizeH3; color: Theme.colorSuccess; font.weight: Font.Bold }
                                Text { text: "DOWNLOAD"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                            }
                            Text {
                                text: Theme.formatRate(bridge?.rxRate ?? 0.0)
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeH2
                                font.weight: Font.Bold
                                color: Theme.colorSuccess
                            }
                            Text {
                                text: "Total: " + Theme.formatBytes(bridge?.rxBytes ?? 0)
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeCaption
                                color: Theme.textSecondary
                            }
                        }

                        // Upload rate
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            RowLayout {
                                spacing: 4
                                Text { text: "↑"; font.pixelSize: Theme.fontSizeH3; color: Theme.colorCyan; font.weight: Font.Bold }
                                Text { text: "UPLOAD"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                            }
                            Text {
                                text: Theme.formatRate(bridge?.txRate ?? 0.0)
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeH2
                                font.weight: Font.Bold
                                color: Theme.colorCyan
                            }
                            Text {
                                text: "Total: " + Theme.formatBytes(bridge?.txBytes ?? 0)
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeCaption
                                color: Theme.textSecondary
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.colorBorder
                    }

                    // Cumulative data bar
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Total Session Transfer: " + Theme.formatBytes((bridge?.rxBytes ?? 0) + (bridge?.txBytes ?? 0))
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeCaption
                            color: Theme.colorGold
                            font.weight: Font.Medium
                        }
                    }
                }
            }

            // 3. Wi-Fi Co-Processor Quick Card
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Wi-Fi Hotspot Co-Processor"
                subtitle: "Broadcom 802.11b/g/n Subsystem"

                RowLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingLg

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: (bridge?.wifiPower ?? false) ? ("SSID: " + ((bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "Active")) : "Wi-Fi Radio Disabled"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeH3
                            font.weight: Font.Bold
                            color: (bridge?.wifiPower ?? false) ? Theme.textPrimary : Theme.textMuted
                        }

                        Text {
                            text: (bridge?.wifiPower ?? false) ? ((bridge?.wifiClientsCount ?? 0) + " client(s) connected") : "Turn on Wi-Fi radio to broadcast SSID"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            color: Theme.textSecondary
                        }
                    }

                    FelineButton {
                        text: (bridge?.wifiPower ?? false) ? "Disable Wi-Fi" : "Enable Wi-Fi"
                        variant: (bridge?.wifiPower ?? false) ? "secondary" : "gold"
                        iconGlyph: "📶"
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.toggleWifi();
                            }
                        }
                    }
                }
            }

            // 4. Daemon & System Environment Card
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Daemon & Architecture State"
                subtitle: "IPC transport and hardware binding"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "DAEMON STATUS:"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                        Text {
                            text: (bridge?.isDaemonRunning ?? false) ? "ONLINE (Active Daemon)" : "DIRECT SERIAL FALLBACK"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            font.weight: Font.Bold
                            color: (bridge?.isDaemonRunning ?? false) ? Theme.colorSuccess : Theme.colorWarning
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "IPC BACKEND:"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                        Text {
                            text: (bridge?.transportMode ? bridge.transportMode.toUpperCase() : "SOCKET")
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            font.weight: Font.Bold
                            color: Theme.colorCyan
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "HARDWARE TARGET:"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                        Text {
                            text: "Qualcomm MDM9600 (Aleka UV310)"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textSecondary
                        }
                    }
                }
            }
        }
    }
}
