import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    property int bars: bridge?.signalBars ?? 0
    property int csq: bridge?.signalCsq ?? 0
    property int dbm: bridge?.signalDbm ?? -113
    property bool isPresent: bridge?.modemPresent ?? false

    // Semantic bar color based on signal level
    readonly property color activeColorStart: {
        if (!isPresent || bars === 0) return Theme.colorDanger;
        if (bars >= 4) return Theme.gradientHeroStart;
        if (bars >= 2) return Theme.gradientWarnStart;
        return Theme.gradientDangerStart;
    }

    readonly property color activeColorEnd: {
        if (!isPresent || bars === 0) return Theme.colorCrimson;
        if (bars >= 4) return Theme.gradientHeroEnd;
        if (bars >= 2) return Theme.gradientWarnEnd;
        return Theme.gradientDangerEnd;
    }

    implicitWidth: 130
    implicitHeight: 140

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacingSm

        // Stepped Cellular Tower Bars
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Row {
                anchors.centerIn: parent
                anchors.bottom: parent.bottom
                spacing: 7

                Repeater {
                    model: 5

                    Rectangle {
                        required property int index
                        readonly property bool isLit: root.isPresent && (index < root.bars)
                        // Stepped height from 22px up to 90px
                        width: 11
                        height: 22 + (index * 17)
                        anchors.bottom: parent.bottom
                        radius: Theme.radiusPill

                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop {
                                position: 0.0
                                color: isLit ? root.activeColorStart : "#161d2c"
                            }
                            GradientStop {
                                position: 1.0
                                color: isLit ? root.activeColorEnd : "#101622"
                            }
                        }

                        border.color: isLit ? Qt.rgba(255, 255, 255, 0.18) : Theme.colorBorder
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: Theme.animNormal } }
                    }
                }
            }
        }

        // Signal Level Badge & Readout
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Layout.alignment: Qt.AlignHCenter

            Text {
                text: {
                    if (!root.isPresent) return "NO SIGNAL";
                    if (root.bars === 0) return "SEARCHING...";
                    return root.bars + " OF 5 BARS";
                }
                font.family: Theme.fontSans
                font.pixelSize: Theme.fontSizeSmall
                font.weight: Font.Bold
                color: (!root.isPresent || root.bars === 0) ? Theme.colorDanger : Theme.textPrimary
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: {
                    if (!root.isPresent) return "Modem Offline";
                    if (root.csq <= 0 || root.csq === 99) return "0 CSQ (— dBm)";
                    return root.csq + " CSQ • " + root.dbm + " dBm";
                }
                font.family: Theme.fontMono
                font.pixelSize: 10
                color: (!root.isPresent) ? Theme.textMuted : Theme.colorCyan
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
