package com.streamflix.app;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
import android.webkit.*;
import android.view.View;
import android.view.WindowManager;

public class MainActivity extends BridgeActivity {

    private static final String[] BLOCKED = {
        "doubleclick.net","googlesyndication.com","googletagmanager.com",
        "googleadservices.com","google-analytics.com","adservice.google.com",
        "pagead2.googlesyndication.com","ads.yahoo.com","advertising.com",
        "adnxs.com","adsrvr.org","adform.net","adroll.com","criteo.com",
        "rubiconproject.com","openx.net","pubmatic.com","appnexus.com",
        "smartadserver.com","taboola.com","outbrain.com","mgid.com",
        "sharethrough.com","bidswitch.net","exoclick.com","trafficjunky.com",
        "juicyads.com","propellerads.com","popads.net","adsterra.com",
        "clickadu.com","adcash.com","yllix.com","trafficstars.com",
        "hotjar.com","mixpanel.com","coin-hive.com","coinhive.com",
        "facebook.net","connect.facebook.net",
    };

    private static final String JS =
        "(function(){" +
        "window.open=function(){return null;};" +
        "window.alert=function(){};" +
        "window.confirm=function(){return true;};" +
        "function rm(){document.querySelectorAll('*').forEach(function(e){" +
        "try{var s=window.getComputedStyle(e),z=parseInt(s.zIndex)||0," +
        "p=s.position,t=e.tagName||'';" +
        "if(z>9000&&(p==='fixed'||p==='absolute')&&t!=='VIDEO'&&t!=='IFRAME')" +
        "{e.remove();}}catch(x){}});}" +
        "setInterval(rm,1500);rm();" +
        "document.addEventListener('click',function(e){" +
        "var a=e.target.closest&&e.target.closest('a');" +
        "if(a&&a.target==='_blank'){e.preventDefault();e.stopPropagation();}},true);" +
        "})();";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        WebView wv = getBridge().getWebView();
        wv.getSettings().setMediaPlaybackRequiresUserGesture(false);
        wv.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        wv.setWebViewClient(new WebViewClient(){
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r){
                String url=r.getUrl().toString().toLowerCase();
                for(String b:BLOCKED){if(url.contains(b))return new WebResourceResponse("text/plain","utf-8",new java.io.ByteArrayInputStream("".getBytes()));}
                if(url.contains("/ads/")||url.contains("popunder")||url.contains("tracker")||url.contains("pixel.")||url.contains("beacon"))
                    return new WebResourceResponse("text/plain","utf-8",new java.io.ByteArrayInputStream("".getBytes()));
                return null;
            }
            @Override
            public void onPageFinished(WebView v,String url){
                super.onPageFinished(v,url);
                v.evaluateJavascript(JS,null);
            }
        });
        wv.setWebChromeClient(new WebChromeClient(){
            private View fv; private CustomViewCallback fc;
            @Override public boolean onCreateWindow(WebView v,boolean d,boolean u,android.os.Message m){return false;}
            @Override public void onShowCustomView(View v,CustomViewCallback c){
                fv=v;fc=c;
                getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
                ((android.widget.FrameLayout)getWindow().getDecorView()).addView(v,new android.widget.FrameLayout.LayoutParams(-1,-1));
            }
            @Override public void onHideCustomView(){
                if(fv==null)return;
                ((android.widget.FrameLayout)getWindow().getDecorView()).removeView(fv);
                fv=null;fc.onCustomViewHidden();
            }
            @Override public void onPermissionRequest(PermissionRequest r){r.grant(r.getResources());}
        });
    }
}
