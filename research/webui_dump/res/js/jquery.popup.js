;(function($) {
    var ie6=!-[1,]&&!window.XMLHttpRequest,init=false;
    $.fn.extend({
        //required arguments ops: title=undefined,text=undefined|url=undefined
        //selectable arguments ops: width=240,height=100,splash=false,timer=1500,type=0,url=undefined,close=undefined,buttons=undefined
        popup: function(ops,callback){
            if(ops.close){
                $('.close>a:eq(0)',o).trigger('click',callback);
                return;
            }            
            var ops = $.extend({width:240,height:100,splash:false,timer:1500,type:0},ops),ol=$('<div id="overlay"/>').appendTo(document.body),o=$('#popup'),htm;
            
            if(ops.url){
                htm = '<iframe width="100%" src="'+ops.url+'" height="100%" frameborder="0" scrolling="auto" id="popup_iframe"/>';
            }else{
                htm = '<div class="text_'+ops.type+'">'+ops.text+'</div>';
            }
                
            var header=$('<div class="header" onselectstart="javascript:return false;"><div class="close"><a href="javascript:;" hidefocus title="Press Esc to close"></a></div><div class="title">'+ops.title+'</div></div>'),
            content=$('<div class="content">'+htm+'</div>'),
            footer=$('<div class="footer"/>'),
            main=$('<div class="main"/>').append(header).append(content).append(footer).wrap('<div class="shadow"/>').width(ops.width-2).height(ops.height-3),
            o=$('<div id="popup"/>').wrapInner(main.parent()).appendTo(document.body);
            var w=document.documentElement.clientWidth,h=document.documentElement.clientHeight,sh=0;
            o.width(ops.width).height(ops.height).css({left:(w-ops.width)/2,top:sh+(h-ops.height)/2}).show();
            
            if (ops.buttons){
                $.each(ops.buttons, function(name,fn) {
                    [].push($('<a href="javascript:;" hidefocus/>').text(name).appendTo(footer).click(function(){fn.apply(this,arguments);return false;}));
                });
                content.height(ops.height-58);
                footer.width(ops.width-4);
            }else{
                content.height(ops.height-32);
                footer.remove();
            }
            
            if(ie6){
                ol.css({position:'absolute',width: Math.max($(window).width(),$(document.body).width()),height: Math.max($(window).height(),$(document.body).height())});
                o.css({position: 'absolute'});
                if(!init){
                    $('head').append('<!--[if lte IE 6]><style>@media screen{* html{overflow-y: hidden;}* html body{height:100%;overflow:auto;}}</style><![endif]-->');
                    init=true;
                }
                var select=$('select').ie6fix(true);
                var iframe=$('iframe').contents().find('select').ie6fix(true); //for iframe
            }
                                        
            $('.close>a:eq(0)',header).mousedown(function(e) {
                e.stopPropagation();
            }).click(function(e,callback) {
                if(callback) callback.apply(this, arguments);
                close();
                return false;
            });
                           
                
            $(window).resize(function(){
                w=document.documentElement.clientWidth;
                h=document.documentElement.clientHeight;
            });

            var ow=o.width(),oh=o.height(),index=new Date().getTime(),moving=false;
            o.css('z-index',index+1);
            ol.css('z-index',index);
          
            $('.title',o).mousedown(function(e){
                moving = true;
                var offset=o.offset();
                var _x=e.pageX-offset.left;  
                var _y=e.pageY-offset.top;               
                $(document).mousemove(function(e){
                    if(moving){  
                        var st=$(window).scrollTop();
                        var x=e.pageX-_x; 
                        var y=e.pageY-_y-st;                              

                        if(x<0)x=0;
                        else if(x>w-ow+6)x=w-ow+6;

                        if(y<4)y=4;
                        else if(y>h-oh+7)y=h-oh+7;                     
                        o.css({top:y,left:x});
                    }  
                });
            });

            $(document).mouseup(function(e){
                moving=false;
                $(document).unbind('mousemove');
            }).bind('keydown.overlay',function(e) {
                (e.keyCode && e.keyCode == 27 && close()); 
            });

            if(ops.splash){
                $('.header>.close',o).remove();
                setTimeout(function(){
                	close();
                	if(callback) callback.apply(this, arguments);
                },ops.timer);
            }

            function close(){
                ol.remove();
                $(o).animate({width:0,height:0,left:w/2,top:h/2},function(){$(this).remove()});
                if(select){
                    select.ie6fix(false);
                    mainFrame.ie6fix(false); //for iframe
                }
            }
        },
        ie6fix: function(flag){
             return ie6?this.css('visibility',flag?'hidden':'visible'):this;
        }        
    });   
})(jQuery);