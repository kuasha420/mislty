import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "."
import "components"
import "views"

ApplicationWindow {
    id: window
    visible: true
    width: 980
    height: 650
    minimumWidth: 850
    minimumHeight: 560
    title: "MisLTy — Qualcomm MDM9600 Suite"
    color: Theme.colorVoid

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ===================================================================
        // TOP HEADER BAR
        // ===================================================================
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: Theme.colorObsidian
            border.color: Theme.colorBorder
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingLg
                anchors.rightMargin: Theme.spacingLg
                spacing: Theme.spacingLg

                // MisLTy Feline Brand & Title
                RowLayout {
                    spacing: Theme.spacingSm
                    Rectangle {
                        width: 34
                        height: 34
                        radius: Theme.radiusMd
                        color: Qt.rgba(243, 156, 18, 0.15)
                        border.color: Theme.colorGold
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "🐾"
                            font.pixelSize: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 0
                        Text {
                            text: "MisLTy"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeH2
                            font.weight: Font.Black
                            color: Theme.colorGold
                        }
                        Text {
                            text: "MDM9600 Linux Suite"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textMuted
                        }
                    }
                }

                // Vertical Divider
                Rectangle {
                    width: 1
                    height: 28
                    color: Theme.colorBorder
                }

                // Live Cellular RF Signal & Carrier
                RowLayout {
                    spacing: Theme.spacingMd

                    SignalBars {
                        bars: bridge?.signalBars ?? 0
                        csq: bridge?.signalCsq ?? 0
                        dbm: bridge?.signalDbm ?? -113
                        offline: !(bridge?.modemPresent ?? false)
                        offlineText: "OFFLINE"
                        showText: true
                    }

                    Rectangle {
                        height: 22
                        width: carrierLabel.implicitWidth + 12
                        radius: Theme.radiusPill
                        color: (bridge?.modemPresent ?? false) ? Qt.rgba(0, 240, 255, 0.1) : Qt.rgba(255, 51, 102, 0.12)
                        border.color: (bridge?.modemPresent ?? false) ? Qt.rgba(0, 240, 255, 0.3) : Qt.rgba(255, 51, 102, 0.4)
                        border.width: 1

                        Text {
                            id: carrierLabel
                            anchors.centerIn: parent
                            text: {
                                if (!(bridge?.modemPresent ?? false)) return "No Modem Detected";
                                if (bridge?.operator && bridge.operator.length > 0) return bridge.operator;
                                return "Searching...";
                            }
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            font.weight: Font.DemiBold
                            color: (bridge?.modemPresent ?? false) ? Theme.colorCyan : Theme.colorDanger
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Hardware Status Pill
                StatusPill {
                    label: "MODEM"
                    value: (bridge?.modemPresent ?? false) ? (bridge?.hardwareStateText ?? "READY") : "OFFLINE"
                    statusColor: {
                        if (!(bridge?.modemPresent ?? false)) return Theme.colorDanger;
                        if (bridge?.isZeroCd ?? false) return Theme.colorWarning;
                        if (bridge?.modemReady ?? false) return Theme.colorSuccess;
                        return Theme.colorWarning;
                    }
                    pulse: !(bridge?.modemPresent ?? false)
                }

                // Wi-Fi Status Pill
                StatusPill {
                    label: "WIFI"
                    value: (bridge?.wifiPower ?? false) ? ((bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "ON") : "OFF"
                    statusColor: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.textMuted
                }

                // Daemon Status Pill
                StatusPill {
                    label: "DAEMON"
                    value: (bridge?.isDaemonRunning ?? false) ? (bridge?.transportMode ? bridge.transportMode.toUpperCase() : "SOCKET") : "DIRECT"
                    statusColor: (bridge?.isDaemonRunning ?? false) ? Theme.colorSuccess : Theme.colorWarning
                    pulse: bridge?.isDaemonRunning ?? false
                }

                // Refresh Action Button
                FelineButton {
                    text: ""
                    iconGlyph: "⟳"
                    variant: "secondary"
                    implicitWidth: 34
                    implicitHeight: 34
                    onClicked: {
                        if (typeof bridge !== "undefined" && bridge) {
                            bridge.refreshStatus();
                        }
                    }
                }
            }
        }

        // ===================================================================
        // MAIN BODY (SIDEBAR + CONTENT DECKS)
        // ===================================================================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // ---------------------------------------------------------------
            // LEFT SIDEBAR NAVIGATION
            // ---------------------------------------------------------------
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 200
                Layout.minimumWidth: 200
                Layout.maximumWidth: 200
                color: Theme.colorObsidian
                border.color: Theme.colorBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: Theme.spacingMd
                    anchors.bottomMargin: Theme.spacingMd
                    spacing: Theme.spacingXs

                    // Nav item Repeater
                    Repeater {
                        model: [
                            { index: 0, label: "Dashboard", icon: "📊", desc: "Overview & Controls" },
                            { index: 1, label: "Wi-Fi Hotspot", icon: "📶", desc: "Co-Processor SoftAP" },
                            { index: 2, label: "SMS Center", icon: "💬", desc: "Conversations & Ingest" },
                            { index: 3, label: "Phone Dialer", icon: "📞", desc: "Voice & PipeWire" },
                            { index: 4, label: "Diagnostics", icon: "⚡", desc: "AT Console & Ports" }
                        ]

                        Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            height: 50
                            color: ((bridge?.activeDeck ?? 0) === modelData.index) ? Theme.colorCard : (navMouse.containsMouse ? Theme.colorCardHover : "transparent")
                            radius: 0

                            Behavior on color { ColorAnimation { duration: Theme.animFast } }

                            // Active accent indicator line on the left
                            Rectangle {
                                width: 3
                                height: parent.height
                                anchors.left: parent.left
                                color: ((bridge?.activeDeck ?? 0) === modelData.index) ? Theme.colorCyan : "transparent"
                            }

                            MouseArea {
                                id: navMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof bridge !== "undefined" && bridge) {
                                        bridge.setActiveDeck(modelData.index);
                                    }
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spacingLg
                                anchors.rightMargin: Theme.spacingMd
                                spacing: Theme.spacingMd

                                Text {
                                    text: modelData.icon
                                    font.pixelSize: 18
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        text: modelData.label
                                        font.family: Theme.fontSans
                                        font.pixelSize: Theme.fontSizeBody
                                        font.weight: ((bridge?.activeDeck ?? 0) === modelData.index) ? Font.Bold : Font.Normal
                                        color: ((bridge?.activeDeck ?? 0) === modelData.index) ? Theme.colorCyan : Theme.textPrimary
                                    }

                                    Text {
                                        text: modelData.desc
                                        font.family: Theme.fontSans
                                        font.pixelSize: Theme.fontSizeSmall
                                        color: Theme.textMuted
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Sidebar Footer Info
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.colorBorder
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.spacingMd
                        Layout.rightMargin: Theme.spacingMd
                        spacing: 2

                        Text {
                            text: {
                                var wanText = (bridge?.connected ?? false) ? "WAN: ppp0 (LTE)" : "WAN: Standby";
                                var relayText = (bridge?.relayActive ?? false) ? (" • AP: " + (bridge?.relayInterface ?? "Active")) : "";
                                return wanText + relayText;
                            }
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            color: (bridge?.connected ?? false) ? Theme.colorGold : Theme.textMuted
                        }

                        Text {
                            text: "MisLTy v1.0.0 • PSL"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textMuted
                        }
                    }
                }
            }

            // ---------------------------------------------------------------
            // CENTRAL CONTENT DECK
            // ---------------------------------------------------------------
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.colorVoid

                StackLayout {
                    id: deckStack
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    currentIndex: bridge?.activeDeck ?? 0

                    DashboardView {
                        id: dashboardView
                    }

                    WifiView {
                        id: wifiView
                    }

                    SmsView {
                        id: smsView
                    }

                    DialerView {
                        id: dialerView
                    }

                    DiagnosticsView {
                        id: diagnosticsView
                    }
                }
            }
        }
    }
}
