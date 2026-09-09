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
	<input type="hidden" value="WIFI_BASIC" name="goformId" id="goformId"> 
    <input type="hidden" value="" name="lucknum_WIFI_BASIC" id="lucknum_WIFI_BASIC">
    
	<table><tr><th id="ui_wifi_profiles">Wi-Fi Profiles</th></tr>          
          <tr> 
            <td width="140" id="ui_network_mode">Network Mode</td>
            <td><select name="wirelessmode" style="width:175px;">			  
				<option value="1" id="ui_n_only">802.11n Only</option>
				<option value="0" id="ui_bgn_mixed">802.11 b/g/n</option>
            </select></td>
          </tr>
          <tr> 
            <td id="ui_network_name">Network Name (SSID)</td>
            <td><input type="text" id="ssid" name="ssid" maxlength="32" value="TypeScript 420" style="width:175px;"></td>
          </tr>
           <tr> 
            <td id="ui_ssid_broadcast">SSID Broadcast</td>
            <td>
              <input type=radio name="broadcastssid" value="1"><span id="ui_enable">Enable</span>
              <input type=radio name="broadcastssid" value="0"><span id="ui_disable">Disable</span>
            </td>
          </tr>
          <tr>
            <td><span id="ui_frequency_channel">Frequency (Channel)</span></td>
            <td>
              <select name="channel" style="width:175px;">
				  <option value="0" id="ui_auto">Auto</option>
				  <option value="1">Channel 1</option>
				  <option value="2">Channel 2</option>
				  <option value="3">Channel 3</option>
				  <option value="4">Channel 4</option>
				  <option value="5">Channel 5</option>
				  <option value="6">Channel 6</option>
				  <option value="7">Channel 7</option>
				  <option value="8">Channel 8</option>
				  <option value="9">Channel 9</option>
				  <option value="10">Channel 10</option>
				  <option value="11">Channel 11</option>
              </select>
            </td>
          </tr>
          <tr>
            <td><span id="ui_max_sataion_number">Max Station Number</span></td>
            <td>
                <select name="Allow_MAX_STAs" style="width:175px;">
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                    <option value="5">5</option>
                    <option value="6">6</option>
                    <option value="7">7</option>
                    <option value="8">8</option>
                </select>
            </td>
          </tr>
          <tr><td></td><td style="font-weight:700;line-height:30px;" id="ui_note">Note: After you click Apply, The Wi-Fi profile settings will be effective after rebooting the uFi device.</td></tr>
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
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
		parent.loading(1000,1);
	});
	if(confirm(text['tip_reboot'])) {
        $.get('/goform/goform_process?goformId=device_reboot');    
	}
}

$(function() {
	$.i18n(lang,'wifi_profile',function(){
		var m = $('select[name=wirelessmode]');
		m.val(0);
		
		
		$('input[name=broadcastssid]:eq('+(1==0?1:0)+')').attr('checked',true);
		
		
		$('select[name=channel]').val(0);
		$('select[name=Allow_MAX_STAs]').val(8);
	});
	parent.setHeight();
});
</script>
</body>
</html>