import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    property int totalSegments: 10
    property int rsrpLevel: {
        if (!(bridge?.modemPresent ?? false)) return 0;
        var dbm = (bridge?.signalDbm ?? -113);
        // -120 dBm (0) to -60 dBm (10)
        return Math.max(0, Math.min(totalSegments, Math.round((dbm + 120) / 6.0)));
    }
    property int rsrqLevel: {
        if (!(bridge?.modemPresent ?? false)) return 0;
        var csq = (bridge?.signalCsq ?? 0);
        // CSQ 0-31 -> 0-10
        return Math.max(0, Math.min(totalSegments, Math.round(csq / 3.1)));
    }
    property int rssiLevel: {
        if (!(bridge?.modemPresent ?? false)) return 0;
        var bars = (bridge?.signalBars ?? 0);
        // 5 bars -> scale to 10
        return Math.max(0, Math.min(totalSegments, bars * 2));
    }

    property color rsrpColor: Theme.colorCyan       // Electric Cyan
    property color rsrqColor: Theme.colorGold       // Radiant Amber
    property color rssiColor: Theme.colorSuccess    // Emerald Green

    implicitWidth: 100
    implicitHeight: 120

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacingMd

        // Column 1: RSRP (Cyan)
        ColumnLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 3

            // Stack of 10 segments (top to bottom = index 9 down to 0)
            Repeater {
                model: root.totalSegments

                delegate: Rectangle {
                    required property int index
                    readonly property int segmentLevel: root.totalSegments - index
                    readonly property bool isLit: segmentLevel <= root.rsrpLevel

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 2
                    color: isLit ? root.rsrpColor : "#182232"
                    opacity: isLit ? 1.0 : 0.6

                    Behavior on color { ColorAnimation { duration: Theme.animNormal } }
                }
            }

            Text {
                text: "RSRP"
                font.family: Theme.fontSans
                font.pixelSize: 10
                font.weight: Font.DemiBold
                color: Theme.textMuted
                Layout.alignment: Qt.AlignHCenter
                topPadding: 4
            }
        }

        // Column 2: RSRQ (Amber)
        ColumnLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 3

            Repeater {
                model: root.totalSegments

                delegate: Rectangle {
                    required property int index
                    readonly property int segmentLevel: root.totalSegments - index
                    readonly property bool isLit: segmentLevel <= root.rsrqLevel

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 2
                    color: isLit ? root.rsrqColor : "#182232"
                    opacity: isLit ? 1.0 : 0.6

                    Behavior on color { ColorAnimation { duration: Theme.animNormal } }
                }
            }

            Text {
                text: "RSRQ"
                font.family: Theme.fontSans
                font.pixelSize: 10
                font.weight: Font.DemiBold
                color: Theme.textMuted
                Layout.alignment: Qt.AlignHCenter
                topPadding: 4
            }
        }

        // Column 3: RSSI (Green)
        ColumnLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 3

            Repeater {
                model: root.totalSegments

                delegate: Rectangle {
                    required property int index
                    readonly property int segmentLevel: root.totalSegments - index
                    readonly property bool isLit: segmentLevel <= root.rssiLevel

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 2
                    color: isLit ? root.rssiColor : "#182232"
                    opacity: isLit ? 1.0 : 0.6

                    Behavior on color { ColorAnimation { duration: Theme.animNormal } }
                }
            }

            Text {
                text: "RSSI"
                font.family: Theme.fontSans
                font.pixelSize: 10
                font.weight: Font.DemiBold
                color: Theme.textMuted
                Layout.alignment: Qt.AlignHCenter
                topPadding: 4
            }
        }
    }
}
