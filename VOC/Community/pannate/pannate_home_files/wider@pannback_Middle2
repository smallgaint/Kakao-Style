(function () {
    var $ad_id = 'criteo-466554'
    var $ad_width = 250;
    var $ad_height = 250;

    var adArea = document.querySelector('.sidebar_banner');

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
                        'zoneId': 1830754,
                        'sizes': ['250x250'],
                        'ext': {
                            'bidder': {
                                'uid': 466554
                            },
                            'floors': {
                                'banner': {
                                    '250x250': {
                                        'floor': 430,
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
                        var htmlcode = '<html><head></head><body><script>\n' +
                            'var pb_src = location.protocol==\'http:\' ? \'http://cyad1.nate.com/js.kti/nate/cri@pann_Middle2\' : \'https://cyad1.nate.com/js.kti/nate/cri@pann_Middle2\'\n' +
                            'document.write(\'<script language=javascript src="\' + pb_src + \'"><\'+\'/scr' + 'ipt>\');\n' +
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
