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
	<input type="hidden" name="goformId" value="WIFI_SECURITY">
    <input type="hidden" name="lucknum_WIFI_SECURITY" value="">
    <input type="hidden" name="security_shared_mode" value="NONE">
    <input type="hidden" name="cipher" value="2">
	<input type="hidden" name="wep_default_key" value="0">
	<input type="hidden" name="wep_key_1" value="">
	<input type="hidden" name="wep_key_2" value="">
	<input type="hidden" name="wep_key_3" value="">
	<input type="hidden" name="wep_key_4" value="">
	<input type="hidden" name="WEP1Select" value="0">
	<input type="hidden" name="WEP2Select" value="1">
	<input type="hidden" name="WEP3Select" value="1">
	<input type="hidden" name="WEP4Select" value="1">
    
	<table width="760"><tr><th id="ui_wifi_security">Wi-Fi Security</th></tr>
        <tr> 
            <td width="140" id="ui_secruity_mode">Security Mode</td>
            <td width="600">
			<div id="droplist_security_mode">
				<p></p>
				<ul>
					<li value="OPEN" id="ui_no_encryption">NO ENCRYPTION</li>
					<li value="WPAPSKWPA2PSK">WPA-PSK/WPA2-PSK</li>
				</ul>
			</div>
            </td>
        </tr>
        <tr><td id="ui_pass_phrase">Pass Phrase</td>
        	<td><input type="text" name="passphrase" value="1234567890" maxlength="10" class="input"> (A-Z,a-z,0-9,-) (8-10 <span id="ui_characters">characters</span>)</td>
        </tr>
        <tr><td></td>
        	<td style="line-height:30px;font-weight:700;" id="ui_note">Note: After you click Apply, The Wi-Fi security settings will be effective after rebooting the uFi device.</td>
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

function select_security_mode(v) {
	var upp = $('#ui_pass_phrase').parent();
	if(v == 'OPEN') {
		upp.hide();
	} else {
		upp.show();
	}
	parent.setHeight();
}

function apply() {
	var pwd=/^[0-9A-Za-z\-]{8,10}$/;
	var k=$('input[name=passphrase]').val();
	if(!pwd.test(k)){
		alert(text['tip_note']);
		return;
	}
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
		parent.loading(1000,1);
	});
	if(confirm(text['tip_reboot'])) {
        $.get('/goform/goform_process?goformId=device_reboot');    
	}
}

$(function() {
	var v = 'WPAPSKWPA2PSK';	
	select_security_mode(v);
	
	$.i18n(lang,'wifi_security',function(){
		$('#droplist_security_mode').droplist('security_mode',v,select_security_mode);
	});
	parent.setHeight();
});
</script>
</body>
</html>