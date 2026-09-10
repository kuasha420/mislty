import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property string dialInput: bridge?.activeCallNumber ?? ""
    property string activeCallState: bridge?.callState ?? "IDLE"
    property int callDuration: bridge?.callDuration ?? 0
    property bool showTragicVoiceModal: bridge?.tragicVoiceVisible ?? false

    function formatDuration(sec) {
        var m = Math.floor(sec / 60);
        var s = sec % 60;
        return (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
    }

    function appendDigit(digit) {
        dialInput += digit;
        if (typeof bridge !== "undefined" && bridge && bridge.sendDtmfTone) {
            bridge.sendDtmfTone(digit);
        }
    }

    function backspace() {
        if (dialInput.length > 0) {
            dialInput = dialInput.substring(0, dialInput.length - 1);
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacingMd

        // Left Card: 12-Button Keypad & Call Control
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Voice Dialer & Keypad"
            subtitle: "PipeWire PCM Loopback Bridge (8000 Hz S16_LE)"

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spacingSm

                // Number Display Screen
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 62
                    Layout.maximumHeight: 62
                    radius: Theme.radiusMd
                    color: Theme.colorObsidian
                    border.color: Theme.colorBorder
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingMd
                        spacing: Theme.spacingMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                spacing: Theme.spacingSm
                                // Call State Badge
                                Rectangle {
                                    implicitHeight: 20
                                    implicitWidth: stateText.implicitWidth + 12
                                    radius: 10
                                    color: {
                                        if (root.activeCallState === "CONNECTED") return Qt.rgba(0, 230, 118, 0.2);
                                        if (root.activeCallState === "DIALING" || root.activeCallState === "ALERTING") return Qt.rgba(243, 156, 18, 0.2);
                                        if (root.activeCallState === "TERMINATED") return Qt.rgba(255, 51, 102, 0.2);
                                        return Qt.rgba(86, 93, 109, 0.2);
                                    }
                                    border.color: {
                                        if (root.activeCallState === "CONNECTED") return Theme.colorSuccess;
                                        if (root.activeCallState === "DIALING" || root.activeCallState === "ALERTING") return Theme.colorGold;
                                        if (root.activeCallState === "TERMINATED") return Theme.colorDanger;
                                        return Theme.colorBorder;
                                    }
                                    border.width: 1

                                    Text {
                                        id: stateText
                                        anchors.centerIn: parent
                                        text: root.activeCallState
                                        font.family: Theme.fontMono
                                        font.pixelSize: 10
                                        font.weight: Font.Bold
                                        color: {
                                            if (root.activeCallState === "CONNECTED") return Theme.colorSuccess;
                                            if (root.activeCallState === "DIALING" || root.activeCallState === "ALERTING") return Theme.colorGold;
                                            if (root.activeCallState === "TERMINATED") return Theme.colorDanger;
                                            return Theme.textMuted;
                                        }
                                    }
                                }

                                Text {
                                    visible: root.activeCallState !== "IDLE"
                                    text: root.formatDuration(root.callDuration)
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: Theme.textSecondary
                                }
                            }

                            // Large Digits
                            Text {
                                text: root.dialInput.length > 0 ? root.dialInput : "Enter number..."
                                font.family: Theme.fontMono
                                font.pixelSize: 20
                                font.weight: Font.Bold
                                color: root.dialInput.length > 0 ? Theme.colorCyan : Theme.textMuted
                                elide: Text.ElideLeft
                                Layout.fillWidth: true
                            }
                        }

                        // Backspace Button
                        Rectangle {
                            width: 36
                            height: 36
                            radius: Theme.radiusSm
                            color: bsHover.containsMouse ? Theme.colorCardHover : "transparent"
                            border.color: Theme.colorBorder
                            border.width: 1
                            visible: root.dialInput.length > 0

                            Text {
                                anchors.centerIn: parent
                                text: "⌫"
                                font.pixelSize: 16
                                color: Theme.textPrimary
                            }

                            MouseArea {
                                id: bsHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.backspace()
                            }
                        }
                    }
                }

                // 12-Button Keypad Grid
                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 3
                    rowSpacing: Theme.spacingSm
                    columnSpacing: Theme.spacingSm

                    Repeater {
                        model: [
                            { digit: "1", sub: "" },
                            { digit: "2", sub: "ABC" },
                            { digit: "3", sub: "DEF" },
                            { digit: "4", sub: "GHI" },
                            { digit: "5", sub: "JKL" },
                            { digit: "6", sub: "MNO" },
                            { digit: "7", sub: "PQRS" },
                            { digit: "8", sub: "TUV" },
                            { digit: "9", sub: "WXYZ" },
                            { digit: "*", sub: "" },
                            { digit: "0", sub: "+" },
                            { digit: "#", sub: "" }
                        ]

                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: 44
                            Layout.minimumHeight: 36
                            radius: Theme.radiusMd
                            color: btnHover.pressed
                                   ? Qt.rgba(0, 240, 255, 0.25)
                                   : (btnHover.containsMouse ? Theme.colorCardHover : Theme.colorObsidian)
                            border.color: btnHover.containsMouse ? Theme.colorCyan : Theme.colorBorder
                            border.width: 1

                            Behavior on color { ColorAnimation { duration: 100 } }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    text: modelData.digit
                                    font.family: Theme.fontMono
                                    font.pixelSize: 22
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: modelData.sub
                                    font.family: Theme.fontSans
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                    color: Theme.colorGold
                                    opacity: 0.8
                                    visible: modelData.sub.length > 0
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }

                            MouseArea {
                                id: btnHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.appendDigit(modelData.digit)
                            }
                        }
                    }
                }

                // Call Action Bar
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    implicitHeight: 40
                    spacing: Theme.spacingMd

                    // Call Button
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radiusMd
                        color: (root.dialInput.length === 0 || root.activeCallState !== "IDLE")
                               ? Theme.colorCardHover
                               : (callBtnHover.containsMouse ? "#00ff88" : Theme.colorSuccess)
                        opacity: (root.dialInput.length === 0 || root.activeCallState !== "IDLE") ? 0.4 : 1.0

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spacingSm
                            Text { text: "📞"; font.pixelSize: 16 }
                            Text {
                                text: "Place Call"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Bold
                                color: Theme.textInverse
                            }
                        }

                        MouseArea {
                            id: callBtnHover
                            anchors.fill: parent
                            enabled: root.dialInput.length > 0 && root.activeCallState === "IDLE"
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge && bridge.dialNumber) {
                                    bridge.dialNumber(root.dialInput);
                                }
                            }
                        }
                    }

                    // Hangup Button
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radiusMd
                        color: (root.activeCallState === "IDLE")
                               ? Theme.colorCardHover
                               : (hangupHover.containsMouse ? "#ff4d79" : Theme.colorDanger)
                        opacity: (root.activeCallState === "IDLE") ? 0.4 : 1.0

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spacingSm
                            Text { text: "📵"; font.pixelSize: 16 }
                            Text {
                                text: "End Call"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Bold
                                color: "#ffffff"
                            }
                        }

                        MouseArea {
                            id: hangupHover
                            anchors.fill: parent
                            enabled: root.activeCallState !== "IDLE"
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge && bridge.hangupCall) {
                                    bridge.hangupCall();
                                }
                            }
                        }
                    }
                }
            }
        }

        // Right Card: Telephony Specs & Lore Teaser
        Card {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            title: "Cellular Voice Specs"
            subtitle: "Qualcomm Baseband Architecture"

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spacingLg

                Rectangle {
                    Layout.fillWidth: true
                    radius: Theme.radiusSm
                    color: Theme.colorObsidian
                    border.color: Theme.colorBorder
                    border.width: 1
                    implicitHeight: specCol.implicitHeight + Theme.spacingMd * 2

                    ColumnLayout {
                        id: specCol
                        anchors.fill: parent
                        anchors.margins: Theme.spacingMd
                        spacing: Theme.spacingSm

                        Text {
                            text: "AUDIO ARCHITECTURE"
                            font.family: Theme.fontMono
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            color: Theme.colorCyan
                        }

                        RowLayout {
                            Text { text: "PCM Format:"; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: "16-bit LE Mono"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textPrimary }
                        }

                        RowLayout {
                            Text { text: "Sample Rate:"; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: "8,000 Hz"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textPrimary }
                        }

                        RowLayout {
                            Text { text: "Voice Port:"; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: "/dev/mislty/voice"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.colorGold }
                        }

                        RowLayout {
                            Text { text: "Audio Bridge:"; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: "PipeWire (pw-cat)"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.colorSuccess }
                        }
                    }
                }

                // Tragic Voice Lore Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Qt.rgba(255, 51, 102, 0.08)
                    border.color: Qt.rgba(255, 51, 102, 0.3)
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingMd
                        spacing: Theme.spacingSm

                        RowLayout {
                            Text { text: "💔"; font.pixelSize: 16 }
                            Text {
                                text: "The Tragic Voice Easter Egg"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                font.weight: Font.Bold
                                color: Theme.colorDanger
                            }
                        }

                        Text {
                            text: "Why does modern LTE reject voice calls on MDM9600? Learn the hardware history of Circuit-Switched Fallback (CSFB) and pure-LTE carrier network transitions."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textSecondary
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }

                        Item { Layout.fillHeight: true }

                        FelineButton {
                            Layout.fillWidth: true
                            text: "Read Tragic Voice Lore"
                            variant: "gold"
                            iconGlyph: "📖"
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge && bridge.triggerTragicVoiceLore) {
                                    bridge.triggerTragicVoiceLore(root.dialInput || "121");
                                } else {
                                    root.showTragicVoiceModal = true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // =======================================================================
    // "Tragic Voice" Lore Modal Dialog
    // =======================================================================
    Rectangle {
        id: tragicVoiceModal
        anchors.fill: parent
        color: Qt.rgba(12, 14, 20, 0.85)
        visible: root.showTragicVoiceModal || (bridge?.tragicVoiceVisible ?? false) || (bridge?.tragicVoiceModalVisible ?? false)
        z: 999

        MouseArea {
            // Block background clicks
            anchors.fill: parent
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width * 0.85, 580)
            implicitHeight: loreCol.implicitHeight + Theme.spacingXl * 2
            radius: Theme.radiusLg
            color: Theme.colorCard
            border.color: Theme.colorGold
            border.width: 1

            ColumnLayout {
                id: loreCol
                anchors.fill: parent
                anchors.margins: Theme.spacingXl
                spacing: Theme.spacingLg

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Text { text: "📻"; font.pixelSize: 22 }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: "The Tragic Voice of MDM9600"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeH2
                            font.weight: Font.Bold
                            color: Theme.colorGold
                        }
                        Text {
                            text: "Circuit-Switched Fallback (CSFB) vs. The Pure-LTE Era"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            color: Theme.textMuted
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.colorBorder
                }

                // Narrative body
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeSmall
                    lineHeight: 1.35
                    color: Theme.textPrimary
                    text: "In the golden era of 3G/HSPA+, Qualcomm MDM9600 was an engineering marvel. It featured a dedicated raw 8000 Hz, 16-bit linear PCM audio stream routed through USB Interface MI_02 (/dev/mislty/voice), allowing Linux computers to act as complete voice handsets.\n\n" +
                          "However, this portable dongle firmware lacks an IP Multimedia Subsystem (IMS) VoLTE client. When you place a voice call today, the baseband requests Circuit-Switched Fallback (CSFB), asking the tower to drop the link to 2G (GSM) or 3G (WCDMA).\n\n" +
                          "Across modern pure-LTE cellular networks (Grameenphone, Banglalink, Robi, Teletalk, and global carriers), 3G has been decommissioned and legacy 2G is barred from CSFB handovers for data dongles. The network core summarily refuses the fallback request, terminating the call with cause #31 or NO CARRIER.\n\n" +
                          "Your MisLTy PipeWire audio bridge and feline dialer are fully functional, but the cellular world has moved on. The voice remains forever locked in silicon."
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.colorBorder
                }

                // Dismiss button
                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    FelineButton {
                        text: "Understood, Good Cat"
                        variant: "primary"
                        iconGlyph: "🐾"
                        implicitWidth: 180
                        implicitHeight: 38
                        onClicked: {
                            root.showTragicVoiceModal = false;
                            if (typeof bridge !== "undefined" && bridge && bridge.dismissTragicVoice) {
                                bridge.dismissTragicVoice();
                            }
                        }
                    }
                }
            }
        }
    }
}
