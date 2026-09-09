<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
</head> 
<body> 
<div class="wrap">
	<table>
	<tr><th id="ui_reset_factory">Reset to Default Factory Settings</th></tr>
	<tr><td class="content">
		<form>
			<input type="hidden" name="action_flag" value="restore">
			<INPUT type="hidden" name="goformId" value="RESTORE" >
			<input type="hidden" name="lucknum_RESTORE" value="">
			<input type="button" class="btn l2"  value="Reset Factory" onclick="reset_factory();" id="btn_reset_factory">
		</form>
	</td></tr>
	</table>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';
if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

$(function() {
	$.i18n(lang,'reset_factory');
	parent.setHeight();
});

function reset_factory() {
	$.post('/goform/goform_process',$('form:eq(0)').serialize());
	$('.content').html('<div style="height:300px;line-height:28px;padding:10px;">You have been logged out. The Device will now restart. <br>Please wait, connection will automatically be re-established if possible. <br>If this fails, it is usually because your Wi-Fi has connected to a different network. </div>');
	parent.setHeight();
	parent.loading(3000,1);
}
</script>
</body>
</html>