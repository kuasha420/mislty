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
	<table class="list"><tr><th colspan="4" class="title" id="ui_basic_status">Basic Status</th></tr>
		<tr>
			<td colspan="4" style="font-weight:700;" id="ui_3g_information">3G Information</td>
		</tr>		
		<tr>
			<td width="130" id="ui_network_provider">Network Provider:</td><td id="provider" width="180"></td>
			<td width="130" id="ui_roam">Roam:</td><td id="roam"></td>  
		</tr>
		<tr>
			<td id="ui_network_type">Network Type:</td><td id="network_type"></td>
			<td id="ui_domain">Domain:</td><td>CS_PS</td>              
		</tr>			
		<tr>
			<td colspan="4" style="font-weight:700;" id="ui_system_information">System Information</td>
		</tr>
		<tr>
			<td id="ui_imei">IMEI:</td><td>861179037820644</td>
			<td id="ui_firmware_version">Firmware version:</td><td>01.01.02</td>
		</tr>
		<tr>
			<td id="ui_software_version">Software version:</td><td>MDM9K-CIGO-U-7.3.9-4M</td>
			<td id="ui_hardware_version">Hardware version:</td><td>HV1.0</td>
		</tr>
	</table>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

var dual_mode_type = 'WCDMA';

$(function() {	
	$.i18n(lang,'basic_status',function(){
		$('#rscp').html(parseInt());
		$('#ecio').html(parseInt(0) / 2);
		
		var roam 		= 'roam_off';
		var spn     	= 'Robi';
		var provider	= '470022596798399';
		var network_type     = 'LTE';
		
		if(roam.isEmpty()) {
			$('#roam').html(text['tip_unknown']);
		} else if (roam.toLowerCase() == 'roam_on') {
			$('#roam').html(text['tip_on']);
		} else {
			$('#roam').html(text['tip_off']);
		}
		
		if(spn.isEmpty()){
			if(provider.isEmpty() || provider == '0') {
				$('#provider').html(text['tip_unknown']);
			} else {
				//$('#provider').html(provider);
				var cimi = '470022596798399';
				if(!cimi.isEmpty()) {
                     $.get('xml/apn_list.xml', function(r) {
                        var apn = $(r).find('apn[cimi='+cimi.substring(0,5)+']').eq(0);
                        if(apn.length == 0 ) {
                            apn = $(r).find('apn[cimi='+cimi.substring(0,6)+']').eq(0);
                        }  
                        $('#provider').html(apn.attr('name'));
                     });
                }
			}
		} else {
			$('#provider').html(spn);
		}
		
		if(network_type.isEmpty() || network_type == '0') {
			$('#network_type').html(text['tip_unknown']);
		} else if(network_type == 'Limited Service') {
			$('#network_type').html(text['tip_limited_service']);
		} else if (network_type == 'No Service') {
			$('#network_type').html(text['tip_no_service']);
		} else {
			$('#network_type').html(network_type);
		}
		
		if(dual_mode_type == 'CDMA') {
            var s = $('#ui_imei');
            s.html('MEID:');
            s.next().html('A100000E70630F');
        }
	});
	
	parent.setHeight();
});
</script>
</body>
</html>