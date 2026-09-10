import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    property var history: []
    property color barColor: Theme.colorSuccess
    property string title: "Throughput"
    property string currentRateStr: "0 B/s"
    property string peakRateStr: "0 B/s"
    property string totalBytesStr: "0 B"
    property string iconGlyph: "↓"

    implicitHeight: 86
    implicitWidth: 260
    radius: Theme.radiusMd
    color: Theme.colorObsidian
    border.color: Theme.colorBorder
    border.width: 1

    function computeMax() {
        var m = 1.0;
        if (!root.history || root.history.length === 0) return m;
        for (var i = 0; i < root.history.length; i++) {
            if (root.history[i] > m) m = root.history[i];
        }
        return m;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingSm
        spacing: 4

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                text: root.iconGlyph
                font.pixelSize: 13
                font.weight: Font.Bold
                color: root.barColor
            }

            Text {
                text: root.title
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSizeSmall
                font.weight: Font.Bold
                color: Theme.textSecondary
            }

            Item { Layout.fillWidth: true }

            Text {
                text: root.currentRateStr
                font.family: Theme.fontMono
                font.pixelSize: 14
                font.weight: Font.Bold
                color: root.barColor
            }
        }

        // Animated Bar Pulse / Sparkline
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            radius: Theme.radiusSm
            color: Theme.colorVoid
            border.color: Qt.rgba(255, 255, 255, 0.05)
            border.width: 1
            clip: true

            Row {
                id: barRow
                anchors.fill: parent
                anchors.margins: 4
                spacing: 2

                property int numBars: (root.history && root.history.length > 0) ? root.history.length : 24
                property real barW: Math.max(3, (width - (numBars - 1) * spacing) / numBars)

                Repeater {
                    model: barRow.numBars

                    Rectangle {
                        required property int index
                        width: barRow.barW
                        anchors.bottom: parent.bottom
                        radius: 1

                        property real val: (root.history && root.history[index] !== undefined) ? Number(root.history[index]) : 0.0
                        property real maxV: root.computeMax()

                        height: Math.max(3, Math.min(parent.height - 2, (val / maxV) * (parent.height - 2)))
                        color: root.barColor
                        opacity: 0.35 + (0.65 * (index / Math.max(1, barRow.numBars - 1)))

                        Behavior on height {
                            NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutQuad }
                        }
                    }
                }
            }
        }

        // Footer: Peak Rate & Total Volume
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Peak: " + root.peakRateStr
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.textMuted
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Total: " + root.totalBytesStr
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.textSecondary
            }
        }
    }
}
