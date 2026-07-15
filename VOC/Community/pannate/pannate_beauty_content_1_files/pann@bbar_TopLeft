(function () {
    var $ad_id = 'criteo-1751240'
    var $ad_width = 970;
    var $ad_height = 120;

    try {
        var $ad_frame = parent.document.querySelector('#pann_brandAdWrap iframe');
        if ($ad_frame.style.height === '0px' || !$ad_frame.style.height) {
            $ad_frame.style.minHeight = $ad_height + 'px';
            $ad_frame.style.height = $ad_height + 'px';
            $ad_frame.setAttribute('height', $ad_height);
        }
        if (parent.document.querySelector('#pann_brandAdWrap').style.display === 'none') {
            parent.document.querySelector('#pann_brandAdWrap').style.display = 'block';
        }
    } catch (e) {
        window.onload = function () {
            window.parent.postMessage({
                "method": "fnct",
                "name": "callCrossOriginAd",
                "property": { target: window.name, height: $ad_height }
            }, '*');
        }
    }
    try {
        var $script = document.createElement('script');
        $script.type = 'text/javascript';
        $script.src = '//static.criteo.net/js/ld/publishertag.js';
        $script.async = true;
        var $ad_frame = parent.document.querySelector('#ad_sponsorIfr');
        var $ad_wrap = document.getElementById('adWrap');

        var $div = document.createElement('div');
        $div.id = $ad_id;


        $script.onload = function () {
            window.Criteo = window.Criteo || {}; window.Criteo.events = window.Criteo.events || [];
            Criteo.events.push(function () {
                var adUnits = {
                    networkId: 1669,
                    publisherId: '108925',
                    placements: [{
                        slotId: $ad_id,
                        zoneId: 1751240,
                        sizes: ['970x120'],
                        ext: {
                            bidder: {
                                uid: 466545
                            },
                            floors: {
                                banner: {
                                    '970x120': {
                                        floor: 400, // set minimum price
                                        currency: 'KRW'
                                    }
                                }
                            }
                        }
                    }]
                };
                Criteo.Passback.RequestBids(adUnits, 2000);
            });

            Criteo.events.push(function () {
                Criteo.Passback.RenderAd($ad_id, function () {
                    var slotid = $ad_id;
                    var div = document.getElementById(slotid);
                    if (div) {
                        var ifr = document.createElement("iframe");
                        ifr.setAttribute("id", slotid + "_iframe"),
                            ifr.setAttribute("frameborder", "0"),
                            ifr.setAttribute("allowtransparency", "true"),
                            ifr.setAttribute("hspace", "0"),
                            ifr.setAttribute("marginwidth", "0"),
                            ifr.setAttribute("marginheight", "0"),
                            ifr.setAttribute("scrolling", "no"),
                            ifr.setAttribute("vspace", "0"),
                            ifr.setAttribute("width", $ad_width),
                            ifr.setAttribute("height", $ad_height);
                        div.appendChild(ifr);
                        var htmlcode = '<html><head></head><body><script language=javascript src="//cyad1.nate.com/js.kti/nate/pannback@bbar_TopLeft"></scr' + "ipt></body></html>";
                        var ifrd = ifr.contentWindow.document;
                        ifrd.open();
                        ifrd.write(htmlcode);
                        ifrd.close();
                    }
                });
            });
        }
        $ad_wrap.appendChild($script);
        $ad_wrap.appendChild($div);
    } catch (e) { }
})();
