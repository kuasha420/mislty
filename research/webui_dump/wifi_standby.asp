<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
</head> 
<body> 
<div class="wrap">
<form>
	<table width="760"><tr><th colspan="2" id="ui_wifi_standby">Wi-Fi Standby</th></tr>
	<input type="hidden" name="goformId" value="WIFI_SLEEP">
	<input type="hidden" value="" name="lucknum_WIFI_SLEEP">
      <tr> 
        <td width="140" id="ui_sleep_mode">Sleep Mode</td>
        <td width="600">
		<div id="droplist_sleep_mode">
			<p></p>
			<ul>
				<li value="0" id="ui_disable">Disable</li>
				<li value="1" id="ui_enable">Enable</li>
			</ul>
		</div>
        </td>
      </tr>
      <tr> 
        <td id="ui_sleep_time">Sleep Time</td>
        <td>			
			<div id="droplist_sleep_time">
				<p></p>
				<ul>
					<li value="5" 	id="ui_5_minutes">5 minutes</li>
					<li value="10" 	id="ui_10_minutes">10 minutes</li>
					<li value="20"	id="ui_20_minutes">20 minutes</li>
					<li value="30"	id="ui_30_minutes">30 minutes</li>
					<li value="60"	id="ui_1_hours">1 hours</li>
					<li value="120"	id="ui_2_hours">2 hours</li>
					<li value="-1"	id="ui_always_on">Always on</li>
				</ul>
			</div>
        </td>
      </tr> 
     <tr><td colspan="2" style="padding-left:135px;">
		<input type="button" class="btn" onclick="apply();" value="Apply"  id="btn_apply"> 
		<input type="button" class="btn" onclick="location.reload();" value="Reset" id="btn_reset">
     </td></tr>
</table>
</form>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

var sleep_time = '-1';

function select_mode(v) {
	var p = $('#ui_sleep_time').parent();
	v == 0 ? p.hide() : p.show();
	parent.setHeight(300);
}

function apply() {
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
		parent.loading(3000,1);
	});
}

$(function() {
	select_mode(sleep_time == '-1' ? 0 :1);
	
	$.i18n(lang,'wifi_standby',function(){
		$('#droplist_sleep_mode').droplist('sleep_mode',sleep_time == '-1' ? 0 :1, select_mode);
		$('#droplist_sleep_time').droplist('sleep_time',sleep_time);
	});
	parent.setHeight(300);
});
</script>
</body>
</html>