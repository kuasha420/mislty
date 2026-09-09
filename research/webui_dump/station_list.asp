<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
</head> 
<body> 
<div class="wrap">	
	<table class="list">
		<tr><th colspan="2" class="title"  id="ui_wireless_network">Wireless Network</th></tr>
		<tr>
			<th align="center" width="50%" id="ui_station">Station</th>
			<th align="center" id="ui_mac_address">MAC Address</th>
		</tr>
		<tr><td align="center" width="40%" class="head">1</td><td align="center" width="60%" class="tail">D2:6F:5B:13:A8:B5</td></tr>
	</table>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

$(function() {
	$.i18n(lang,'station_list');
	parent.setHeight();
});
</script>
</body>
</html>