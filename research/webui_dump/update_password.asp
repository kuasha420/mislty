<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
</head> 
<body> 
<div class="wrap">
	<table width="750"><tr><th id="ui_update_password">Update Password</th></tr>
	<form>
		<input type="hidden" value="USER_MODIFY" name="goformId">
		<input type="hidden" value="" name="lucknum_USER_MODIFY">			
			<tr>
				<td width="140" id="ui_current_password">Current Password</td>
				<td width="600"><input type="password" maxlength="32" size="20" name="current_passwd" id="current_passwd"></td>
			</tr>
            <tr>
				<td id="ui_new_password">New Password</td>
				<td><input type="password" maxlength="32" size="20" name="admpass" id="admpass"></td>
			</tr>
			<tr>
				<td id="ui_reenter_password">Re-enter Password</td>
				<td><input type="password" maxlength="32" size="20" name="adm_confirm_pass" id="adm_confirm_pass"></td>
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

function apply() {
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function() {
		$.get('util/update_password_result.asp',function(r) {
			if(r == 'success') {
				parent.loading(1000,1);
			} else {
				alert('Current password is incorrect!');
			}
		});		
	});
}

$(function() {
	$.i18n(lang,'update_password');
	parent.setHeight();
});
</script>
</body>
</html>