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

                // MisLTy Brand with Gradient Squircle Mark (matching concept artwork)
                RowLayout {
                    spacing: Theme.spacingSm
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 8
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: Theme.gradientHeroStart }
                            GradientStop { position: 1.0; color: Theme.gradientHeroEnd }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: "M"
                            font.family: Theme.fontSans
                            font.pixelSize: 18
                            font.weight: Font.Black
                            font.italic: true
                            color: "#ffffff"
                        }
                    }

                    Text {
                        text: "MisLTy"
                        font.family: Theme.fontSans
                        font.pixelSize: 18
                        font.weight: Font.Bold
                        color: "#ffffff"
                    }
                }

                // Vertical Divider
                Rectangle {
                    width: 1
                    height: 20
                    color: Theme.colorBorder
                }

                // Signal Indicator + Status Pill + Band Pill (matching concept artwork)
                RowLayout {
                    spacing: Theme.spacingMd

                    // Signal bars with dBm label centered underneath
                    ColumnLayout {
                        spacing: 2
                        Layout.alignment: Qt.AlignVCenter

                        SignalBars {
                            bars: bridge?.signalBars ?? 0
                            csq: bridge?.signalCsq ?? 0
                            dbm: bridge?.signalDbm ?? -113
                            offline: !(bridge?.modemPresent ?? false)
                            offlineText: ""
                            showText: false
                        }

                        Text {
                            text: "dBm"
                            font.family: Theme.fontSans
                            font.pixelSize: 9
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }

                    // LTE Status Pill (dark green pill with emerald dot and text)
                    Rectangle {
                        height: 28
                        width: lteRow.implicitWidth + 24
                        radius: Theme.radiusPill
                        color: (bridge?.connected ?? false) ? "#072a20" : ((bridge?.modemPresent ?? false) ? Qt.rgba(56, 189, 248, 0.12) : Qt.rgba(244, 63, 94, 0.12))
                        border.color: (bridge?.connected ?? false) ? "#059669" : ((bridge?.modemPresent ?? false) ? Qt.rgba(56, 189, 248, 0.3) : Qt.rgba(244, 63, 94, 0.35))
                        border.width: 1

                        RowLayout {
                            id: lteRow
                            anchors.centerIn: parent
                            spacing: 8

                            Rectangle {
                                width: 7
                                height: 7
                                radius: 3.5
                                color: (bridge?.connected ?? false) ? "#10b981" : ((bridge?.modemPresent ?? false) ? Theme.colorCyan : Theme.colorDanger)
                            }

                            Text {
                                text: {
                                    if (bridge?.connected ?? false) return "LTE Connected";
                                    if (bridge?.modemPresent ?? false) return "Modem Ready";
                                    return "No Modem Detected";
                                }
                                font.family: Theme.fontSans
                                font.pixelSize: 12
                                font.weight: Font.Medium
                                color: (bridge?.connected ?? false) ? "#34d399" : ((bridge?.modemPresent ?? false) ? Theme.colorCyan : Theme.colorDanger)
                            }
                        }
                    }

                    // Band Pill (vibrant solid cyan pill matching concept artwork)
                    Rectangle {
                        height: 28
                        width: bandText.implicitWidth + 24
                        radius: Theme.radiusPill
                        visible: bridge?.modemPresent ?? false
                        color: "#22d3ee"

                        Text {
                            id: bandText
                            anchors.centerIn: parent
                            text: (bridge?.bandName && bridge.bandName.length > 0) ? bridge.bandName : "Band 3"
                            font.family: Theme.fontSans
                            font.pixelSize: 12
                            font.weight: Font.Bold
                            color: "#082f49"
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Clean Right Utility Icons (matching concept artwork: bell, user, log-out)
                RowLayout {
                    spacing: 8

                    // Notifications / Alerts
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: bellHover.containsMouse ? Qt.rgba(255, 255, 255, 0.08) : "transparent"
                        Icon {
                            anchors.centerIn: parent
                            name: "bell"
                            size: 16
                            color: Theme.textMuted
                        }
                        MouseArea {
                            id: bellHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                        }
                    }

                    // User Profile
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: userHover.containsMouse ? Qt.rgba(255, 255, 255, 0.08) : "transparent"
                        Icon {
                            anchors.centerIn: parent
                            name: "user"
                            size: 16
                            color: Theme.textMuted
                        }
                        MouseArea {
                            id: userHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                        }
                    }

                    // Log out / Exit
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: logoutHover.containsMouse ? Qt.rgba(255, 255, 255, 0.08) : "transparent"
                        Icon {
                            anchors.centerIn: parent
                            name: "log-out"
                            size: 16
                            color: Theme.textMuted
                        }
                        MouseArea {
                            id: logoutHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Qt.quit()
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
            // LEFT SIDEBAR NAVIGATION (SINGLE-LINE CLEAN ITEMS)
            // ---------------------------------------------------------------
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 180
                Layout.minimumWidth: 170
                Layout.maximumWidth: 190
                color: Theme.colorObsidian
                border.color: Theme.colorBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: Theme.spacingLg
                    anchors.bottomMargin: Theme.spacingMd
                    spacing: 6

                    // Nav item Repeater (matching concept navigation list)
                    Repeater {
                        model: [
                            { index: 0, label: "Dashboard", icon: "dashboard" },
                            { index: 1, label: "Wi-Fi", icon: "wifi" },
                            { index: 2, label: "SMS", icon: "message-square" },
                            { index: 3, label: "Dialer", icon: "phone" },
                            { index: 4, label: "Diagnostics", icon: "terminal" },
                            { index: 5, label: "Settings", icon: "settings" }
                        ]

                        Rectangle {
                            required property var modelData
                            readonly property bool isActive: (bridge?.activeDeck ?? 0) === modelData.index
                            Layout.fillWidth: true
                            Layout.leftMargin: 10
                            Layout.rightMargin: 10
                            height: 42
                            radius: 12
                            color: isActive ? "#162032" : (navMouse.containsMouse ? "#121826" : "transparent")
                            border.width: 0

                            Behavior on color { ColorAnimation { duration: Theme.animFast } }

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
                                anchors.leftMargin: 14
                                anchors.rightMargin: 12
                                spacing: 12

                                Icon {
                                    name: modelData.icon
                                    size: 17
                                    color: isActive ? Theme.colorCyan : (navMouse.containsMouse ? Theme.textPrimary : Theme.textMuted)
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    font.family: Theme.fontSans
                                    font.pixelSize: 14
                                    font.weight: isActive ? Font.DemiBold : Font.Normal
                                    color: isActive ? Theme.colorCyan : (navMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Clean Minimalist Sidebar Footer (matching concept artwork)
                    Text {
                        text: "MisLTy v1.0.0"
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeSmall
                        color: "#475569"
                        Layout.alignment: Qt.AlignHCenter
                        Layout.bottomMargin: 8
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

                    Card {
                        id: settingsCard
                        title: "Application Settings"
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingMd
                            Text {
                                text: "MisLTy Qualcomm MDM9600 Cellular & Auxiliary Wi-Fi Suite"
                                font.family: Theme.fontSans
                                font.pixelSize: 14
                                color: Theme.textPrimary
                            }
                            Text {
                                text: "Version 1.0.0 • Connected Hardware: " + ((bridge?.modemPresent ?? false) ? "Qualcomm MDM9600" : "Offline")
                                font.family: Theme.fontSans
                                font.pixelSize: 12
                                color: Theme.textSecondary
                            }
                        }
                    }
                }
            }
        }
    }
}
