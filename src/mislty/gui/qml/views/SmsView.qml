import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property int activeThreadId: -1
    property string activeRecipient: ""
    property string activeContactName: ""
    property string searchQuery: ""

    Component.onCompleted: {
        if (typeof bridge !== "undefined" && bridge) {
            bridge.getSmsThreads();
        }
    }

    // Helper to filter threads list by search query
    function getFilteredThreads() {
        var raw = (typeof bridge !== "undefined" && bridge) ? (bridge.smsThreads ?? []) : [];
        if (!root.searchQuery || root.searchQuery.trim() === "") {
            return raw;
        }
        var q = root.searchQuery.toLowerCase().trim();
        var res = [];
        for (var i = 0; i < raw.length; i++) {
            var item = raw[i];
            var num = (item.recipient_number || "").toLowerCase();
            var name = (item.contact_name || "").toLowerCase();
            var snip = (item.snippet || "").toLowerCase();
            if (num.indexOf(q) !== -1 || name.indexOf(q) !== -1 || snip.indexOf(q) !== -1) {
                res.push(item);
            }
        }
        return res;
    }

    function formatThreadTime(ts) {
        if (!ts) return "";
        if (typeof ts === "number") {
            var date = new Date(ts * 1000);
            var now = new Date();
            var isToday = (date.toDateString() === now.toDateString());
            var h = date.getHours();
            var m = date.getMinutes();
            var timeStr = (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m);
            if (isToday) return timeStr;
            var month = date.getMonth() + 1;
            var day = date.getDate();
            return month + "/" + day + " " + timeStr;
        }
        if (typeof ts === "string") {
            return ts.length >= 16 ? ts.substring(11, 16) : ts;
        }
        return "";
    }

    function sendActiveMessage() {
        var targetNumber = recipientInput.text.trim();
        var content = msgInput.text.trim();
        if (!targetNumber || !content) return;

        if (typeof bridge !== "undefined" && bridge) {
            var ok = bridge.sendSms(targetNumber, content);
            if (ok) {
                msgInput.text = "";
                if (root.activeThreadId > 0) {
                    bridge.getSmsMessages(root.activeThreadId);
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingXl
        spacing: Theme.spacingLg

        // ===================================================================
        // Left Pane: SMS Threads / Search / Ingest
        // ===================================================================
        Card {
            Layout.fillHeight: true
            Layout.preferredWidth: 340
            title: "Conversations"
            subtitle: "SQLite Threaded Archive"

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spacingMd

                // Action Bar: Sync SIM & New Thread
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    FelineButton {
                        Layout.fillWidth: true
                        text: "Sync SIM"
                        variant: "gold"
                        iconGlyph: "🔄"
                        implicitHeight: 34
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.syncSms();
                            }
                        }
                    }

                    FelineButton {
                        text: "New Message"
                        variant: "secondary"
                        iconGlyph: "✏️"
                        implicitWidth: 115
                        implicitHeight: 34
                        onClicked: {
                            root.activeThreadId = -1;
                            root.activeRecipient = "";
                            root.activeContactName = "";
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.smsMessages = [];
                            }
                            recipientInput.forceActiveFocus();
                        }
                    }
                }

                // Search Bar
                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.colorObsidian
                    border.color: searchInput.activeFocus ? Theme.colorCyan : Theme.colorBorder
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacingSm
                        spacing: Theme.spacingSm

                        Text {
                            text: "🔍"
                            font.pixelSize: 12
                            opacity: 0.6
                        }

                        TextInput {
                            id: searchInput
                            Layout.fillWidth: true
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textPrimary
                            selectByMouse: true
                            onTextChanged: root.searchQuery = text

                            Text {
                                text: "Filter conversations..."
                                visible: !searchInput.text
                                color: Theme.textMuted
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeSmall
                            }
                        }

                        // Clear search button
                        Text {
                            text: "✕"
                            visible: searchInput.text.length > 0
                            font.pixelSize: 11
                            color: Theme.textMuted
                            MouseArea {
                                anchors.fill: parent
                                onClicked: searchInput.text = ""
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.colorBorder
                }

                // Threads List
                ListView {
                    id: threadsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: root.getFilteredThreads()

                    delegate: Rectangle {
                        id: threadItem
                        required property var modelData
                        width: threadsList.width
                        height: 60
                        radius: Theme.radiusSm
                        color: (modelData.id === root.activeThreadId)
                               ? Qt.rgba(0, 240, 255, 0.12)
                               : (itemHover.containsMouse ? Theme.colorCardHover : "transparent")
                        border.color: (modelData.id === root.activeThreadId) ? Theme.colorCyan : "transparent"
                        border.width: 1

                        MouseArea {
                            id: itemHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.activeThreadId = modelData.id;
                                root.activeRecipient = modelData.recipient_number ? modelData.recipient_number : (modelData.recipient ? modelData.recipient : "");
                                root.activeContactName = modelData.contact_name || "";
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.getSmsMessages(modelData.id);
                                    bridge.markAsRead(modelData.id);
                                }
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingMd
                            spacing: Theme.spacingSm

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    Text {
                                        text: (modelData.contact_name && modelData.contact_name.length > 0)
                                              ? modelData.contact_name
                                              : (modelData.recipient_number ? modelData.recipient_number : (modelData.recipient ? modelData.recipient : "Unknown"))
                                        font.family: modelData.contact_name ? Theme.fontSans : Theme.fontMono
                                        font.pixelSize: Theme.fontSizeBody
                                        font.weight: Font.Bold
                                        color: (modelData.id === root.activeThreadId) ? Theme.colorCyan : Theme.textPrimary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: root.formatThreadTime(modelData.updated_at || modelData.last_time)
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeSmall
                                        color: Theme.textMuted
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingSm

                                    Text {
                                        text: modelData.snippet ? modelData.snippet : (modelData.last_message ? modelData.last_message : "No messages")
                                        font.family: Theme.fontSans
                                        font.pixelSize: Theme.fontSizeCaption
                                        color: Theme.textSecondary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    // Unread Badge
                                    Rectangle {
                                        visible: modelData.unread_count > 0
                                        height: 18
                                        implicitWidth: Math.max(18, unreadText.implicitWidth + 8)
                                        radius: 9
                                        color: Theme.colorGold

                                        Text {
                                            id: unreadText
                                            anchors.centerIn: parent
                                            text: modelData.unread_count
                                            font.family: Theme.fontMono
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                            color: Theme.textInverse
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Empty state
                    Text {
                        anchors.centerIn: parent
                        visible: threadsList.count === 0
                        text: searchInput.text.length > 0 ? "No conversations match filter." : "No SMS threads yet.\nClick 'Sync SIM' to retrieve messages from SIM card."
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeCaption
                        color: Theme.textMuted
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        // ===================================================================
        // Right Pane: Active Thread Transcript & Composer
        // ===================================================================
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: root.activeRecipient.length > 0
                   ? (root.activeContactName.length > 0 ? (root.activeContactName + " (" + root.activeRecipient + ")") : ("Thread: " + root.activeRecipient))
                   : "Compose Message"
            subtitle: root.activeThreadId > 0 ? "3GPP SMS Conversation" : "Send direct SMS message"

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spacingMd

                // Conversation Action Toolbar (when thread is selected)
                RowLayout {
                    Layout.fillWidth: true
                    visible: root.activeThreadId > 0
                    spacing: Theme.spacingSm

                    Text {
                        text: "Active Thread #" + root.activeThreadId
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSizeSmall
                        color: Theme.textMuted
                    }

                    Item { Layout.fillWidth: true }

                    // Quick Dial shortcut button
                    Rectangle {
                        implicitHeight: 28
                        implicitWidth: callRow.implicitWidth + 12
                        radius: Theme.radiusSm
                        color: callHover.containsMouse ? Theme.colorCardHover : Theme.colorObsidian
                        border.color: Theme.colorBorder
                        border.width: 1

                        RowLayout {
                            id: callRow
                            anchors.centerIn: parent
                            spacing: 4
                            Text { text: "📞"; font.pixelSize: 11 }
                            Text {
                                text: "Call"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textPrimary
                            }
                        }

                        MouseArea {
                            id: callHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.activeCallNumber = root.activeRecipient;
                                    bridge.activeDeck = 3; // Switch to Dialer deck
                                }
                            }
                        }
                    }

                    // Delete Thread button
                    Rectangle {
                        implicitHeight: 28
                        implicitWidth: delRow.implicitWidth + 12
                        radius: Theme.radiusSm
                        color: deleteHover.containsMouse ? Qt.rgba(255, 51, 102, 0.2) : Theme.colorObsidian
                        border.color: deleteHover.containsMouse ? Theme.colorCrimson : Theme.colorBorder
                        border.width: 1

                        RowLayout {
                            id: delRow
                            anchors.centerIn: parent
                            spacing: 4
                            Text { text: "🗑️"; font.pixelSize: 11 }
                            Text {
                                text: "Delete"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeSmall
                                color: deleteHover.containsMouse ? Theme.colorCrimson : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            id: deleteHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.activeThreadId > 0 && typeof bridge !== "undefined" && bridge) {
                                    bridge.deleteThread(root.activeThreadId);
                                    root.activeThreadId = -1;
                                    root.activeRecipient = "";
                                    root.activeContactName = "";
                                }
                            }
                        }
                    }
                }

                // Messages Scroll Area
                ListView {
                    id: messagesList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: Theme.spacingMd
                    topMargin: Theme.spacingSm
                    bottomMargin: Theme.spacingSm
                    model: bridge?.smsMessages ?? []

                    // Auto scroll to bottom on new messages
                    onCountChanged: {
                        Qt.callLater(() => { messagesList.positionViewAtEnd(); });
                    }

                    delegate: ChatBubble {
                        required property var modelData
                        width: messagesList.width
                        direction: modelData.direction || "IN"
                        body: modelData.body || ""
                        timestamp: modelData.timestamp || 0
                        status: modelData.status || "DELIVERED"
                        senderNumber: modelData.phone_number || ""
                    }

                    Text {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 40, 420)
                        wrapMode: Text.WordWrap
                        visible: messagesList.count === 0
                        text: root.activeRecipient.length > 0
                              ? "No messages in this conversation yet."
                              : "Select a conversation from the left pane or compose a new SMS below."
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeBody
                        color: Theme.textMuted
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.colorBorder
                }

                // ===========================================================
                // Composer Area
                // ===========================================================
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    // Recipient row (visible/editable when creating new message or changing recipient)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        Text {
                            text: "To:"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textSecondary
                            Layout.preferredWidth: 26
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 34
                            radius: Theme.radiusSm
                            color: Theme.colorObsidian
                            border.color: recipientInput.activeFocus ? Theme.colorCyan : Theme.colorBorder
                            border.width: 1

                            TextInput {
                                id: recipientInput
                                anchors.fill: parent
                                anchors.margins: Theme.spacingSm
                                text: root.activeRecipient
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textPrimary
                                selectByMouse: true
                                onTextChanged: {
                                    if (root.activeThreadId <= 0) {
                                        root.activeRecipient = text;
                                    }
                                }

                                Text {
                                    text: "Phone number (e.g. +8801...)"
                                    visible: !recipientInput.text
                                    color: Theme.textMuted
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                }
                            }
                        }
                    }

                    // Message input and Send button
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: Math.max(64, Math.min(120, msgInput.implicitHeight + Theme.spacingMd * 2))
                            radius: Theme.radiusSm
                            color: Theme.colorObsidian
                            border.color: msgInput.activeFocus ? Theme.colorCyan : Theme.colorBorder
                            border.width: 1

                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: Theme.spacingSm
                                clip: true
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                                TextArea {
                                    id: msgInput
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textPrimary
                                    placeholderTextColor: Theme.textMuted
                                    rightPadding: 16
                                    wrapMode: Text.Wrap
                                    selectByMouse: true
                                    background: null

                                    placeholderText: "Type text message... (Press Ctrl+Enter to send)"

                                    Keys.onReturnPressed: (event) => {
                                        if (event.modifiers & Qt.ControlModifier) {
                                            root.sendActiveMessage();
                                            event.accepted = true;
                                        }
                                    }
                                }
                            }
                        }

                        FelineButton {
                            text: "Send"
                            variant: "primary"
                            iconGlyph: "➤"
                            implicitWidth: 100
                            implicitHeight: 44
                            disabled: !recipientInput.text || !msgInput.text
                            onClicked: root.sendActiveMessage()
                        }
                    }

                    // Character counter & segment summary indicator
                    RowLayout {
                        id: counterRow
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        readonly property var segData: (typeof bridge !== "undefined" && bridge && bridge.calculateSmsSegments)
                                                       ? bridge.calculateSmsSegments(msgInput.text)
                                                       : { "summary": msgInput.text.length + "/160 (1 SMS)", "is_unicode": false, "encoding": "GSM-7" }

                        // Encoding tag
                        Rectangle {
                            implicitHeight: 20
                            implicitWidth: encTag.implicitWidth + 10
                            radius: 4
                            color: counterRow.segData.is_unicode ? Qt.rgba(243, 156, 18, 0.2) : Qt.rgba(0, 240, 255, 0.15)
                            border.color: counterRow.segData.is_unicode ? Theme.colorGold : Theme.colorCyan
                            border.width: 1

                            Text {
                                id: encTag
                                anchors.centerIn: parent
                                text: counterRow.segData.encoding || "GSM-7"
                                font.family: Theme.fontMono
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                color: counterRow.segData.is_unicode ? Theme.colorGold : Theme.colorCyan
                            }
                        }

                        // Usage summary
                        Text {
                            text: counterRow.segData.summary || ""
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textSecondary
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: "Shortcut: Ctrl+Enter"
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeSmall
                            color: Theme.textMuted
                        }
                    }
                }
            }
        }
    }
}
