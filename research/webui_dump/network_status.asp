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
	<table class="list"><tr><th colspan="4" class="title" id="ui_network_status_title">Network Status</th></tr>
		<tr>
			<td colspan="4" style="font-weight:700;" id="ui_wan_information">WAN Information</td></tr>		
			<td width="130" id="ui_network_status">Network Status:</td><td id="ppp_state" width="180"></span></td>
			<td width="130" id="ui_primary_dns">Primary DNS:</td><td id="p_dns"></td>
		</tr>
		<tr>
			<td id="ui_ip_address1">IP Address:</td><td>10.88.109.123</td>
			<td id="ui_secondary_dns">Secondary DNS:</td><td id="s_dns"></td>
		</tr>
		<tr>
			<td colspan="4" style="font-weight:700;" id="ui_wlan_current_status">WLAN Current Status</td>
		</tr>
		<tr>
			<td id="ui_ssid">SSID:</td><td><pre id="ssid"></pre></td>
			<td id="ui_channel">Channel:</td><td id="channel"></td>
		</tr>
		<tr><td id="ui_security_mode">Security Mode:</td><td id="security" colspan="3"></td>
		</tr>
		<tr><td colspan="4" style="font-weight:700;" id="ui_lan_and_wlan_information">LAN and WLAN Information</td></tr>
		<tr>
			<td id="ui_subnet_mask">Subnet Mask:</td><td>255.255.255.0</td>
			<td id="ui_default_gateway">Default Gateway:</td><td>192.168.100.1</td>
		</tr>
		<tr>
			<td id="ui_dhcp_server">DHCP Server:</td><td id="dhcp_state"></td>
			<td id="ui_ip_address2">IP Address:</td><td>192.168.100.1</td>
		</tr>
	</table>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

$(function() {	
	$.i18n(lang,'network_status',function(){
		var ssid = 'TypeScript 420';
		var channel = 0;
		var dhcp_mode  = '1';
		var ppp_status = 'ppp_connected';
		var wps_enabled_state  = '0';
		var encryption   = 'TKIP CCMP';
		var encryptType = 'WPAPSKWPA2PSK';
		var encryptType_tmp = '';	
		
		$('#ssid').html(ssid.isEmpty() ? text['tip_unknown'] : ssid);
		$('#channel').html(channel == '0' ? text['tip_auto'] : channel);
		
		if (ppp_status == 'ppp_connected') {
			$('#ppp_state').html(text['tip_connected']);
		} else if (ppp_status == 'ppp_on_demand') {
			$('#ppp_state').html(text['tip_ondemand']);
		} else {
			$('#ppp_state').html(text['tip_disconnected']);
		}
		
		if (dhcp_mode == '0') {
			$('#dhcp_state').html(text['tip_disable']);
		} else if (dhcp_mode == '1') {
			$('#dhcp_state').html(text['tip_enable']);
		} else {
			$('#dhcp_state').html(text['tip_unknown']);
		}
		
		if ('auto' == 'auto'){
			$('#p_dns').html('10.17.160.102');
			$('#s_dns').html('103.242.23.166');
		}else{
			$('#p_dns').html('');
			$('#s_dns').html('');
		}

		if(wps_enabled_state == '0') {	//wps disabled
			if(encryptType == 'OPEN' && encryption == 'NONE') {
				$('#security').html(text['tip_open']);
			} else {
				if(encryptType=='OPEN')	{
					$('#security').html('OPEN WEP'); 
				} else if(encryptType=='SHARED') {
					$('#security').html('SHARED');
				} else if(encryptType=='WPAPSK') {
					$('#security').html('WPA-PSK');
				} else if(encryptType=='WPA2PSK') {
					$('#security').html('WPA2-PSK');
				} else if(encryptType=='WPAPSKWPA2PSK') {
					$('#security').html('WPA-PSK/WPA2-PSK');
				} else {
					$('#security').html(text['tip_undefined']);
				}
				
			}
		} else {
			if(encryptType_tmp == 'WPAPSK') {
				$('#security').html('WPA-PSK');
			} else if(encryptType_tmp=='WPA2PSK') {
				$('#security').html('WPA2-PSK');
			} else if(encryptType_tmp=='WPAPSKWPA2PSK') {
				$('#security').html('WPA-PSK/WPA2-PSK');
			}
		}
	});
	parent.setHeight();
});
</script>
</body>
</html>