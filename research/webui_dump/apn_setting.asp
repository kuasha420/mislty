<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
    <style>table td {padding:3px 8px;}</style>
</head> 
<body> 
<div class="wrap">
    <table class="list"><tr><th colspan="2" id="ui_apn_setting" class="title">APN Settings</th></tr>
    <form action="/goform/goform_process">
    <input type="hidden" name="goformId" value="APN_UPDATE">
    <input type="hidden" value="" name="lucknum_APN_UPDATE">
      <tr> 
        <td id="ui_apn_name" width="100">Network Provider</td>
        <td width="660">
            <select name="cimi" onchange="select_cimi(this)"></select>
        </td>
      </tr> 
      <tr style="display:none;"> 
        <td id="ui_cimi">CIMI</td>
        <td>
            <input type="text" name="input_cimi">
        </td>
      </tr>
      <tr> 
        <td id="ui_dial_number">Dial Number</td>
        <td></td>
      </tr> 
      <tr> 
        <td id="ui_username">Username</td>
        <td></td>
      </tr> 
      <tr> 
        <td id="ui_password">Password</td>
        <td></td>
      </tr> 
      <tr> 
        <td id="ui_auth">Authentication</td>
        <td>
            <input type="radio" name="auth_mode" value="1"> PAP
            <input type="radio" name="auth_mode" value="2"> CHAP
            <input type="radio" name="auth_mode" value="3"> Auto
        </td>
      </tr> 
      <tr> 
        <td id="ui_apn">APN</td>
        <td></td>
      </tr> 
      <tr><td colspan="2" style="font-weight:700;" id="ui_note">Note: Add, modify, delete APN information after the device will automatically restart.</td></tr>
</table>
<div style="padding-left:110px;" id="btn_ops">
    <input type="button" class="btn" onclick="add();" value="Add"  id="btn_add"> 
    <input type="button" class="btn" onclick="edit();" value="Edit"  id="btn_edit"> 
    <input type="button" class="btn" onclick="del();" value="Del"  id="btn_del">
</div>
<div style="padding-left:110px;">
    <input type="hidden" name="cimi">
    <input type="hidden" name="apn_params">
    <input type="hidden" name="ops" value="SET"> <!-- ADD,DEL,EDIT,SET -->
    <input type="button" class="btn" onclick="apply();" value="Apply"  id="btn_apply"> 
    <input type="button" class="btn" onclick="location.reload();" value="Reset" id="btn_reset">
</div>
</form>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
    top.location.href = 'login.asp';
}

var cimi = '470022596798399';  //'46001';
var apn_info =''; //'China Unicom,46001,*99#2,2,2,uninet2,3'; // ; 

function add(){
    $('#ui_apn_name').next().html('<input type="text" name="apn_name">');
    $('#ui_dial_number').next().html('<input type="text" name="dial_number">');
    $('#ui_username').next().html('<input type="text" name="username">');
    $('#ui_password').next().html('<input type="text" name="password">');
    $('#ui_apn').next().html('<input type="text" name="apn">');
    $('input[name=auth_mode]:eq(2)').attr('checked',true);
    $('#btn_apply').parent().show();
    $('#ui_cimi').parent().show();
    $('input[name=ops]').val('ADD');
    $('#btn_ops').hide();
}

function edit(){
    var apn_name = $('#ui_apn_name').next();
    var dial_number = $('#ui_dial_number').next();
    var username = $('#ui_username').next();
    var password = $('#ui_password').next();
    var apn = $('#ui_apn').next();

    var cs = apn_name.find('select[name=cimi]')
    var cimi;

    if(cs.length == 0) {
        apn_name.html('<input type="text" name="apn_name" value="'+apn_name.html()+'">');
        cimi =  $('input[name=cimi]').val();
    } else {
        apn_name.html('<input type="text" name="apn_name" value="'+cs.find('option').eq(cs[0].options.selectedIndex).html()+'">');
        cimi = cs.val();
    }
    
    dial_number.html('<input type="text" name="dial_number" value="'+dial_number.html()+'">');
    username.html('<input type="text" name="username" value="'+username.html()+'">');
    password.html('<input type="text" name="password" value="'+password.html()+'">');
    apn.html('<input type="text" name="apn" value="'+apn.html()+'">');
    $('#btn_apply').parent().show();
    $('#ui_cimi').parent().show();
    $('input[name=input_cimi]').attr('disabled',true).val(cimi);
    $('input[name=ops]').val('EDIT');
    $('#btn_ops').hide();
}

function del(){
    if(confirm(text['tip_del'])) {
        var apn_name = $('#ui_apn_name').next();
        var cs = apn_name.find('select[name=cimi]')
        var cimi;

        if(cs.length == 0) {
            apn_name = apn_name.html();
            cimi =  $('input[name=cimi]').val();
        } else {
            apn_name = cs.find('option').eq(cs[0].options.selectedIndex).html();
            cimi = cs.val();
        }

        var dial_number = $('#ui_dial_number').next().html();
        var username = $('#ui_username').next().html();
        var password = $('#ui_password').next().html();
        var apn = $('#ui_apn').next().html();
        var auth = $('input[name=auth_mode]:checked').val();

        $('input[name=apn_params]').val(apn_name+','+cimi+','+dial_number+','+username+','+password+','+apn+','+auth);
        $('input[name=ops]').val('DEL');
        $('input[name=input_cimi]').remove();
        $('input[name=cimi]').remove();
        $.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
            parent.loading(1000,1);
        });
    }
}

function select_cimi(o) {
    var i = o.options.selectedIndex;
    $.get('xml/apn_list.xml', function(r) {
        var apn = $(r).find('apn[cimi^='+cimi.substring(0,5)+']').eq(i);
        $('#ui_dial_number').next().html(apn.attr('phone'));
        $('#ui_username').next().html(apn.attr('user'));
        $('#ui_password').next().html(apn.attr('pwd'));
        $('#ui_apn').next().html(apn.attr('domain'));
        $('input[name=auth_mode]:eq('+(parseInt(apn.attr('auth'))-1)+')').attr('checked',true);
        $('input[name=cimi]').val(apn.attr('cimi'));
        $('input[name=apn_params]').val(apn.attr('name')+','+apn.attr('cimi')+','+apn.attr('phone')+','+apn.attr('user')+','+apn.attr('pwd')+','+apn.attr('domain')+','+apn.attr('auth'));
    });  
}

function apply() {
    var ops = $('input[name=ops]').val();
    var apn_name = $('input[name=apn_name]').val();
    var cimi = $('input[name=input_cimi]').val();
    var dial_number = $('input[name=dial_number]').val();
    var username = $('input[name=username]').val();
    var password = $('input[name=password]').val();
    var apn = $('input[name=apn]').val();
    var auth = $('input[name=auth_mode]:checked').val();
    $('input[name=cimi]').val(cimi);
    $('input[name=input_cimi]').remove();

    if(ops == 'ADD') {
        $('input[name=apn_params]').val(apn_name+','+cimi+','+dial_number+','+username+','+password+','+apn+','+auth);
    } else if (ops == 'EDIT'){
        $('input[name=apn_params]').val(apn_name+','+cimi+','+dial_number+','+username+','+password+','+apn+','+auth);
    } else if(ops == 'SET') {
        $('input[name=cimi]').remove();
    }
    $.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
        parent.loading(1000,1);
    });
}

$(function() {
    $.i18n(lang,'apn_setting',function() {
        if(cimi.isEmpty()) {
            $('div[class=wrap]').html('<div style="color:#f00;font-weight:700;">'+text['tip_notice']+'</div>');
        } else {
            $.get('xml/apn_list.xml', function(r) {
                var apns = $(r).find('apn[cimi^='+cimi.substring(0,5)+']'); 
                var apn;  
                if(apns.length == 0 ) {
                    apn = $(r).find('apn[cimi=46001]');
                    $('#ui_apn_name').next().html(apn.attr('name'));
                    $('input[name=cimi]').val('46001');
                    $('input[name=auth_mode]:eq(2)').attr('checked',true);
                    $('#btn_apply').parent().hide();
                } else if(apns.length == 1) {
                    apn = apns.eq(0);
                    $('#ui_apn_name').next().html(apn.attr('name'));
                    $('input[name=cimi]').val(apn.attr('cimi'));
                    $('input[name=auth_mode]:eq('+(parseInt(apn.attr('auth'))-1)+')').attr('checked',true);
                    $('#btn_apply').parent().hide();
                } else if (apns.length > 1) {
                    var cs = $('select[name=cimi]');
                    var index = 0;
                    apns.each(function(i) {
                        var self = $(this);
                        cs[0].options[i] = new Option(self.attr('name'), self.attr('cimi')); 
                        if(self.attr('name') == apn_info.substring(0,apn_info.indexOf(','))) {
                            index = i;
                        }
                    });
                    var apn = apns.eq(index);
                    cs[0].options.selectedIndex = index;
                    $('input[name=cimi]').val(apn.attr('cimi'));
                    $('input[name=apn_params]').val(apn.attr('name')+','+apn.attr('cimi')+','+apn.attr('phone')+','+apn.attr('user')+','+apn.attr('pwd')+','+apn.attr('domain')+','+apn.attr('auth'));
                }
                
                $('#ui_dial_number').next().html(apn.attr('phone'));
                $('#ui_username').next().html(apn.attr('user'));
                $('#ui_password').next().html(apn.attr('pwd'));
                $('#ui_apn').next().html(apn.attr('domain'));
                $('input[name=auth_mode]:eq('+(parseInt(apn.attr('auth'))-1)+')').attr('checked',true);
            });  
        }
    });
    parent.setHeight(340);
});
</script>
</body>
</html>