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
    <input type="hidden" value="NET_CONNECT" name="goformId">
    <input type="hidden" value="" name="lucknum_NET_CONNECT">
	<table><tr><th id="ui_connection_mode">Connection Mode</th></tr>
		<tr><td>
			<input type="radio" value="auto_dial" name="dial_mode">
			<span id="ui_automatic_dialup">Automatic Dial-up</span> 
		</td></tr>
		<tr><td>
			<input type="radio" value="manual_dial" name="dial_mode">
			<span id="ui_manual_dialup">Manual Dial-up</span> 
		</td></tr>
		<tr><td>
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

function apply() {
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
		parent.loading(3000,1);
	});
}

$(function() {
	$('input[name=dial_mode][value=auto_dial]').attr('checked',true);
	$.i18n(lang,'connection_mode');
	parent.setHeight();
});
</script>
</body>
</html>