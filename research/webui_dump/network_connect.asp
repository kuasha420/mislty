<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
</head> 
<body>
<div class="wrap">
	<div style="float:left;width:230px;height:300px;">
		<table style="height:279px;border:1px #ccc solid;">
			<tr><td align="center"><img src="res/img/disconnected.gif" id="connect_logo"></td></tr>
			<tr><td style="line-height:24px;padding-left:20px;">
				<span id="ui_current_flux">Current Flux:</span> <span id="current_flux"></span><br>
				<span id="ui_total_flux">Total Flux:</span> <span id="total_flux"></span><br>
				<span id="ui_connected_time">Connected Time:</span> <span id="connected_time"></span><br>
				<div style="padding-left:50px;margin:2px;"><img src="res/img/upload.jpg" style="vertical-align:middle"> <span id="speed_up"></span> /s</div>
				<div style="padding-left:50px;margin:2px;"><img src="res/img/download.jpg" style="vertical-align:middle"> <span id="speed_down"></span> /s</div>
			</td></tr>
			<tr><td align="center">
			<form>
				<input type="hidden" value="NET_CONNECT" name="goformId" id="goformId">
				<input type="hidden" value="" name="lucknum_NET_CONNECT" id="lucknum_NET_CONNECT">
				<input type="hidden" id="dial_mode" name="dial_mode" value="auto_dial">
				<input type="hidden" name="action" id="action" value="connect">
				<input type="hidden" name="wan_conn_which_page" id="wan_conn_which_page" value="wan_operation">
				<input type="button" class="btn" onclick="connect_ctrl();" value="Connect" id="btn_connect"> 
				<input type="button" class="btn" onclick="location.reload();" value="Refresh" id="btn_refresh">
			</form>
			</td></tr>
		</table>
	</div>
	<div style="margin-left:250px;width:505px;height:300px;">
		<table class="list">
		<tr><th colspan="2" class="title" id="ui_wireless_network">Wireless Network</th></tr>
		<tr>
			<th align="center" width="50%" id="ui_station">Station</th>
			<th align="center" id="ui_mac_address">MAC Address</th>
		</tr>
		<tr><td align="center" width="40%" class="head">1</td><td align="center" width="60%" class="tail">D2:6F:5B:13:A8:B5</td></tr>
		</table>
	</div>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

var timer;

// <!--var network_type = <--% asp_get("network_type"); %-->
var dial_mode = 'auto_dial';
var roam_setting_option='on';
var m_netselect_status = '';
var btn_connect, action, connect_logo;

function transUnit(data) {
	var level = 0;
	var value = Number(data);
	var cal = function() {
		if(value >= 1024 && level != 3) {
			value = value/1024;
			level += 1;
			cal();
		}
	}
	
	cal();
	var unitArr = ['Bytes', 'KB', 'MB', 'GB', 'GB'];
	return Math.round(value*100)/100 + ' ' + (unitArr[level]);
}

function transTime(secs) {
	var hour = Math.floor(secs/3600);
	secs = secs%3600;
	var minu = Math.floor(secs/60);
	secs = secs%60;
	return lpad(hour,2,'0') + ':' + lpad(minu,2,'0') + ':' + lpad(secs,2,'0');
}

function lpad(value, length, placeholder) {
	var len = value.toString().length;
	for(; len  < length; len++) {
		value = placeholder + value;
	}
	return value;
}

function update_state(){
	$.getJSON('json/refresh_data.asp?'+Math.random(),function(data){
		var realtime_statistics = data.realtime_statistics;
		var ppp_status = data.ppp_status
		var cardstate=data.cardstate;
		var roam = data.roam;

		if (ppp_status == 'ppp_connected'){
	 		btn_connect.val(text['tip_disconnect']);
	 		action.val('disconnect');
		} else {
			btn_connect.val(text['tip_connect']);
			action.val('connect');
		}
	 
		if(ppp_status == 'ppp_connecting') {
			connect_logo.src = 'res/img/connecting.gif'; 
		} else if(ppp_status == 'ppp_connected') {
			connect_logo.src = 'res/img/connected.gif'; 
		} else 	if(ppp_status == 'ppp_disconnecting'){
			connect_logo.src = 'res/img/disconnecting.gif'; 		   
		} else {
			connect_logo.src = 'res/img/disconnected.gif'; 
		}

		if (ppp_status != 'ppp_connected') {
			$('#current_flux,#total_flux,#connected_time,#speed_up,#speed_down').html('');
			clearInterval(timer);
			return false;
	 	}

	 	if ( !realtime_statistics ) {
			realtime_statistics = '0,0,0,0,0,0,0,0';
		}

		var array = realtime_statistics.split(',');
		$('#current_flux').html(transUnit(Number(array[2])+Number(array[3])));
		$('#total_flux').html(transUnit(Number(array[5])+Number(array[6])));
		$('#connected_time').html(transTime(array[4]));
		$('#speed_up').html(transUnit(array[0]));
		$('#speed_down').html(transUnit(array[1]));
	});
}

function connect_ctrl() {
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r){
		parent.loading(3000,1);
		location.reload();
	});
}

$(function() {
	$.i18n(lang,'network_connect',function(){
		timer = setInterval(update_state,1000);
	});
	parent.setHeight();
	btn_connect = $('#btn_connect');
	action = $('#action');
	connect_logo = $('#connect_logo')[0];
});
</script>
</body>
</html>