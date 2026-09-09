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
	<input type="hidden" value="DHCP_SET" name="goformId">
    <input type="hidden" value="" name="lucknum_DHCP_SET">
	<table>
	<tr><th colspan="2" id="ui_dhcp_settings">DHCP Settings</th></tr>
	<tr>
		<td width="140" id="ui_ip_address">IP Address</td>
		<td><input id="lan_ip" name="lanIp" maxlength="15" value="192.168.100.1" class="input"></td>
	</tr>
	<tr>
		<td id="ui_subnet_mask">Subnet Mask</td>
		<td><input id="lan_netmask" name="lanNetmask" maxlength="15" value="255.255.255.0" class="input"></td>
	</tr>
	<tr><td id="ui_mac_address">MAC Address</td><td>38:1c:23:04:c6:2c</td></tr>
	<tr><td id="ui_dhcp_ip_pool">DHCP IP Pool</td><td>
			<input id="dhcp_start" name="dhcpStart" maxlength="15" value="192.168.100.100" class="input">&nbsp;&nbsp; - &nbsp;&nbsp;
            <input id="dhcp_end" name="dhcpEnd" maxlength="15" value="192.168.100.200" class="input">
     </td></tr>
     <tr><td id="ui_dhcp_lease_time">DHCP Lease Time</td><td><input name="dhcpLease" id="dhcp_lease" maxlength="5" value="24" class="input">
            &nbsp;<span id="ui_hour">hour(s)</span></td></tr>
     <tr><td></td><td style="font-weight:700;" id="ui_note">Note: Your settings will be effective after rebooting your device.</td></tr>
     <tr><td colspan="2" style="padding-left:135px;">
        <input type="hidden" name="lanDhcpType" value="SERVER">
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
	top.location.href ='login.asp';
}


function apply() {
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
		parent.loading(2000,1);
	});
	if(confirm(text['tip_reboot'])) {
        $.get('/goform/goform_process?goformId=device_reboot');    
	}
}

$(function() {
	//var v = dhcp_enable==0?'DISABLE':'SERVER';
	//select_dhcp(v);
		
	$.i18n(lang,'dhcp_setting'/*,function(){
		$('#droplist_dhcp_server').droplist('lanDhcpType',v,select_dhcp);
	}*/);
	parent.setHeight();
});
</script>
</body>
</html>