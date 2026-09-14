import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    property var rxHistory: (typeof bridge !== "undefined" && bridge?.trafficHistoryRx) ? bridge.trafficHistoryRx : []
    property var txHistory: (typeof bridge !== "undefined" && bridge?.trafficHistoryTx) ? bridge.trafficHistoryTx : []
    property real rxRate: (typeof bridge !== "undefined" && bridge?.rxRate) ? bridge.rxRate : 0.0
    property real txRate: (typeof bridge !== "undefined" && bridge?.txRate) ? bridge.txRate : 0.0

    property color dlColor: "#38bdf8"       // Electric Cyan
    property color ulColor: "#f59e0b"       // Radiant Amber

    implicitHeight: 140
    implicitWidth: 320
    clip: true

    function formatRate(bytesPerSec) {
        if (!bytesPerSec || bytesPerSec <= 0) return "0 B/s";
        var b = Number(bytesPerSec);
        if (b < 1024) return b.toFixed(0) + " B/s";
        var kb = b / 1024;
        if (kb < 1024) return kb.toFixed(1) + " KB/s";
        var mb = kb / 1024;
        if (mb < 1024) return mb.toFixed(1) + " MB/s";
        var gb = mb / 1024;
        return gb.toFixed(2) + " GB/s";
    }

    onRxRateChanged: canvas.requestPaint()
    onTxRateChanged: canvas.requestPaint()
    onRxHistoryChanged: canvas.requestPaint()
    onTxHistoryChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var w = width;
            var h = height;
            if (w <= 10 || h <= 10) return;

            // Generate 8 control nodes across width
            var numPoints = 8;
            var rxPoints = [];
            var txPoints = [];

            var baseline = h * 0.88;
            var topY = h * 0.15;
            var usableH = baseline - topY;

            // Subtle baseline & mid grid guides
            ctx.beginPath();
            ctx.moveTo(0, baseline);
            ctx.lineTo(w, baseline);
            ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.beginPath();
            ctx.setLineDash([4, 6]);
            ctx.moveTo(0, baseline - usableH * 0.5);
            ctx.lineTo(w, baseline - usableH * 0.5);
            ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.setLineDash([]);

            // Process real traffic history arrays (values in KB/s)
            var rawRx = (root.rxHistory && root.rxHistory.length > 0) ? root.rxHistory : [];
            var rawTx = (root.txHistory && root.txHistory.length > 0) ? root.txHistory : [];
            var numPoints = Math.max(24, Math.max(rawRx.length, rawTx.length));

            var rxData = [];
            var txData = [];
            for (var p = 0; p < numPoints - rawRx.length; p++) rxData.push(0.0);
            for (var p = 0; p < rawRx.length; p++) rxData.push(Number(rawRx[p]) || 0.0);

            for (var p = 0; p < numPoints - rawTx.length; p++) txData.push(0.0);
            for (var p = 0; p < rawTx.length; p++) txData.push(Number(rawTx[p]) || 0.0);

            // Compute dynamic peak scale with minimum 10.0 KB/s ceiling
            var rxPeak = 10.0;
            var txPeak = 10.0;
            var hasRxTraffic = root.rxRate > 0;
            var hasTxTraffic = root.txRate > 0;

            for (var i = 0; i < numPoints; i++) {
                if (rxData[i] > 0.05) hasRxTraffic = true;
                if (txData[i] > 0.05) hasTxTraffic = true;
                if (rxData[i] > rxPeak) rxPeak = rxData[i];
                if (txData[i] > txPeak) txPeak = txData[i];
            }

            var rxPoints = [];
            var txPoints = [];

            for (var i = 0; i < numPoints; i++) {
                var x = (w / (numPoints - 1)) * i;

                var rVal = rxData[i];
                var rNorm = hasRxTraffic ? Math.min(1.0, Math.max(0.0, rVal / rxPeak)) : 0.0;
                var rY = baseline - (rNorm * usableH * 0.88);
                rxPoints.push({ x: x, y: rY });

                var tVal = txData[i];
                var tNorm = hasTxTraffic ? Math.min(1.0, Math.max(0.0, tVal / txPeak)) : 0.0;
                var tY = baseline - (tNorm * usableH * 0.65);
                txPoints.push({ x: x, y: tY });
            }

            // Function to draw smooth spline through points using midpoint Bezier
            function drawSpline(points) {
                if (!points || points.length < 2) return;
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 0; i < points.length - 1; i++) {
                    var p0 = points[i];
                    var p1 = points[i + 1];
                    var midX = (p0.x + p1.x) / 2;
                    var midY = (p0.y + p1.y) / 2;
                    ctx.quadraticCurveTo(p0.x, p0.y, midX, midY);
                }
                ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
            }

            // 1. Draw Download (Cyan) Area Fill
            if (hasRxTraffic) {
                ctx.beginPath();
                drawSpline(rxPoints);
                ctx.lineTo(w, baseline);
                ctx.lineTo(0, baseline);
                ctx.closePath();
                var gradDl = ctx.createLinearGradient(0, topY, 0, baseline);
                gradDl.addColorStop(0.0, "rgba(56, 189, 248, 0.25)");
                gradDl.addColorStop(0.8, "rgba(56, 189, 248, 0.04)");
                gradDl.addColorStop(1.0, "rgba(56, 189, 248, 0.0)");
                ctx.fillStyle = gradDl;
                ctx.fill();
            }

            // 2. Draw Download (Cyan) Stroke Line
            ctx.beginPath();
            drawSpline(rxPoints);
            ctx.strokeStyle = hasRxTraffic ? root.dlColor : Qt.rgba(56/255, 189/255, 248/255, 0.25);
            ctx.lineWidth = hasRxTraffic ? 2.2 : 1.2;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.stroke();

            // 3. Draw Upload (Amber) Area Fill
            if (hasTxTraffic) {
                ctx.beginPath();
                drawSpline(txPoints);
                ctx.lineTo(w, baseline);
                ctx.lineTo(0, baseline);
                ctx.closePath();
                var gradUl = ctx.createLinearGradient(0, topY + usableH * 0.35, 0, baseline);
                gradUl.addColorStop(0.0, "rgba(245, 158, 11, 0.22)");
                gradUl.addColorStop(0.8, "rgba(245, 158, 11, 0.04)");
                gradUl.addColorStop(1.0, "rgba(245, 158, 11, 0.0)");
                ctx.fillStyle = gradUl;
                ctx.fill();
            }

            // 4. Draw Upload (Amber) Stroke Line
            ctx.beginPath();
            drawSpline(txPoints);
            ctx.strokeStyle = hasTxTraffic ? root.ulColor : Qt.rgba(245/255, 158/255, 11/255, 0.20);
            ctx.lineWidth = hasTxTraffic ? 1.8 : 1.0;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.stroke();
        }
    }

    // Floating Rate Labels (matching concept artwork: clean, floating near wave crests)
    ColumnLayout {
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.top: parent.top
        anchors.topMargin: 4
        spacing: 16

        Text {
            text: "DL: " + root.formatRate(root.rxRate)
            font.family: Theme.fontMono
            font.pixelSize: 11
            font.weight: Font.DemiBold
            color: root.rxRate > 0 ? root.dlColor : Qt.rgba(56/255, 189/255, 248/255, 0.6)
            Layout.alignment: Qt.AlignRight
        }

        Text {
            text: "UL: " + root.formatRate(root.txRate)
            font.family: Theme.fontMono
            font.pixelSize: 11
            font.weight: Font.DemiBold
            color: root.txRate > 0 ? root.ulColor : Qt.rgba(245/255, 158/255, 11/255, 0.6)
            Layout.alignment: Qt.AlignRight
        }
    }
}
