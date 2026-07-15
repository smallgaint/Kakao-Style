(function () {
    var $ad_id = 'criteo-466557'
    var $ad_width = 300;
    var $ad_height = 250;

    var adArea = document.querySelector('.page_btm_ad .ad');

    try {
        var $script = document.createElement('script');
        $script.type = 'text/javascript';
        $script.src = '//static.criteo.net/js/ld/publishertag.js';
        $script.async = true;

        var $div = document.createElement('div');
        $div.id = $ad_id;

        $script.onload = function () {
            window.Criteo = window.Criteo || {}; window.Criteo.events = window.Criteo.events || [];

            Criteo.events.push(function () {
                var adUnits = {
                    'networkId': 1669,
                    'publisherId': '108926',
                    'placements': [{
                        'slotid': $ad_id,
                        'zoneId': 1830757,
                        'sizes': ['300x250'],
                        'ext': {
                            'bidder': {
                                'uid': 466557
                            },
                            'floors': {
                                'banner': {
                                    '300x250': {
                                        'floor': 100,
                                        'currency': 'KRW'
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
                        var ifr = document.createElement('iframe');
                        ifr.setAttribute('id', slotid + '_iframe'),
                            ifr.setAttribute('frameborder', '0'),
                            ifr.setAttribute('allowtransparency', 'true'),
                            ifr.setAttribute('hspace', '0'),
                            ifr.setAttribute('marginwidth', '0'),
                            ifr.setAttribute('marginheight', '0'),
                            ifr.setAttribute('scrolling', 'no'),
                            ifr.setAttribute('vspace', '0'),
                            ifr.setAttribute('width', $ad_width),
                            ifr.setAttribute('height', $ad_height);
                        div.appendChild(ifr);
                        var htmlcode = '<html><head></head><body><script language=javascript>\n' +
                            'var pb_src = location.protocol==\'http:\' ? \'http://cyad1.nate.com/js.kti/nate/cri@pannback_Middle1\' : \'https://cyad1.nate.com/js.kti/nate/cri@pannback_Middle1\'\n' +
                            'document.write("<scr" + "ipt language=javascript src=\'" + pb_src + (typeof(window.top.ASPQ_4Nca8h)!="undefined" && window.top.ASPQ_4Nca8h!="" ? "?" + window.top.ASPQ_4Nca8h : "") + "\'></scr" + "ipt>");\n' +
                            '</scr' + 'ipt></body></html>';
                        var ifrd = ifr.contentWindow.document;
                        ifrd.open();
                        ifrd.write(htmlcode);
                        ifrd.close();
                    }
                });
            });
        }

        adArea.appendChild($script);
        adArea.appendChild($div);
    } catch (e) { console.warn(e) }
})();
