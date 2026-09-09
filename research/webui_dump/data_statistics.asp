<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
    <style>td{padding-left:8px;}</style>
</head> 
<body> 
<div class="wrap">
<form>
	<input type="hidden" name="action_flag" value="ALL">
    <input type="hidden" value="DATA_STATISTICS_CLEAR" name="goformId">
    <input type="hidden" name="lucknum_DATA_STATISTICS_CLEAR" value="">
    
	<table class="list">
		<tr><th colspan="5" class="title" id="ui_data_statistics">Data Statistics</th></tr>       
        <tr>
			<td width="140" style="text-align:center;font-weight:700;vertical-align:middle;" rowspan="2" id="ui_speed">Rate</td>
			<td style="font-weight:700;" colspan="2" id="ui_up">Upload</td>
			<td style="font-weight:700;" colspan="2" id="ui_download">Download</td>
		</tr>
		<tr>
			<td id="speed_up_value" colspan="2"></td>
			<td id="speed_download_value" colspan="2"></td>
		</tr>
		<tr><td colspan="5">&nbsp;</td></tr>
          <tr>
            <td>&nbsp;</td>
            <td style="font-weight:700;" width="140" id="ui_connected_time">Connected Time</td>
            <td style="font-weight:700;" width="140" id="ui_downloaded">Downloaded</td>
            <td style="font-weight:700;" width="140" id="ui_uploaded">Uploaded</td>
            <td style="font-weight:700;" id="ui_total_traffic">Total Traffic</td>
          </tr>
          <tr>
            <td style="text-align:center;font-weight:700;" id="ui_current">Current</td>
            <td id="current_time_value"></td>
            <td id="current_receive_value"></td>
            <td id="current_transmit_value"></td>
            <td id="current_total"></td>
          </tr>
          <tr>
            <td style="text-align:center;font-weight:700;" id="ui_total">Total</td>
            <td id="total_time_value"></td>
            <td id="total_receive_value"></td>
            <td id="total_transmit_value"></td>
            <td id="total"></td>
          </tr>
          <tr><td colspan="5" style="font-weight:700;" id="ui_note">Note: Your settings will be effective after rebooting your device.</td></tr>
     </table>
     <div><input type="button" class="btn" value="Clear" id="btn_clear" onclick="clear_data();"></div>
</form>	
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}


var realtime_statistics = '0,0,196,168,455,61732223,898445230,57500';

function startRequest() {  
	$.getJSON('json/refresh_data.asp?'+Math.random(),function(data){
		realtime_statistics = data.realtime_statistics;
		ppp_status = data.ppp_status
		cardstate=data.cardstate;
		 roam = data.roam;
		 initValue();
	});
}

function getstatus() {   
     startRequest();
     setTimeout('getstatus()', 1000);
}

function initValue() {
	var array = new Array();
	if ( !realtime_statistics ) {
		realtime_statistics = '0,0,0,0,0,0,0,0';
	}
	array = realtime_statistics.split(',');
	
	$('#speed_up_value').html(transUnit(array[0]) + '/s');
	$('#speed_download_value').html(transUnit(array[1]) + '/s');
	$('#current_transmit_value').html(transUnit(array[2])); 
	$('#current_receive_value').html(transUnit(array[3]));
	$('#current_time_value').html(transTime(array[4])); 
	$('#total_transmit_value').html(transUnit(array[5])); 
	$('#total_receive_value').html(transUnit(array[6]));
	$('#total_time_value').html(transTime(array[7]));
	$('#current_total').html(transUnit(Number(array[2]) + Number(array[3])));
	$('#total').html(transUnit(Number(array[5]) + Number(array[6])));
}

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

function clear_data() {
    $.get('/goform/goform_process?goformId=DATA_STATISTICS_CLEAR&action_flag=ALL&lucknum_DATA_STATISTICS_CLEAR=',function(r){
		parent.loading(1000,1);
	});
}

$(function() {
	$.i18n(lang,'data_statistics');
	parent.setHeight();
	initValue();
	getstatus();
});
</script>
</body>
</html>