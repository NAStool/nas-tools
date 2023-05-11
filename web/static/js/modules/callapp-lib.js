(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
  typeof define === 'function' && define.amd ? define(factory) :
  (global = global || self, global.CallApp = factory());
}(this, (function () { 'use strict';

  function _classCallCheck(instance, Constructor) {
    if (!(instance instanceof Constructor)) {
      throw new TypeError("Cannot call a class as a function");
    }
  }

  function _defineProperties(target, props) {
    for (var i = 0; i < props.length; i++) {
      var descriptor = props[i];
      descriptor.enumerable = descriptor.enumerable || false;
      descriptor.configurable = true;
      if ("value" in descriptor) descriptor.writable = true;
      Object.defineProperty(target, descriptor.key, descriptor);
    }
  }

  function _createClass(Constructor, protoProps, staticProps) {
    if (protoProps) _defineProperties(Constructor.prototype, protoProps);
    if (staticProps) _defineProperties(Constructor, staticProps);
    return Constructor;
  }

  function _defineProperty(obj, key, value) {
    if (key in obj) {
      Object.defineProperty(obj, key, {
        value: value,
        enumerable: true,
        configurable: true,
        writable: true
      });
    } else {
      obj[key] = value;
    }

    return obj;
  }

  function _extends() {
    _extends = Object.assign || function (target) {
      for (var i = 1; i < arguments.length; i++) {
        var source = arguments[i];

        for (var key in source) {
          if (Object.prototype.hasOwnProperty.call(source, key)) {
            target[key] = source[key];
          }
        }
      }

      return target;
    };

    return _extends.apply(this, arguments);
  }

  var ua = navigator.userAgent || ''; // 版本号比较

  var semverCompare = function semverCompare(verionA, versionB) {
    // eslint-disable-next-line no-restricted-properties
    var _window = window,
        isNaN = _window.isNaN;
    var splitA = verionA.split('.');
    var splitB = versionB.split('.');

    for (var i = 0; i < 3; i++) {
      var snippetA = Number(splitA[i]);
      var snippetB = Number(splitB[i]);
      if (snippetA > snippetB) return 1;
      if (snippetB > snippetA) return -1; // e.g. '1.0.0-rc' -- Number('0-rc') = NaN

      if (!isNaN(snippetA) && isNaN(snippetB)) return 1;
      if (isNaN(snippetA) && !isNaN(snippetB)) return -1;
    }

    return 0;
  };
  /**
   * 获取 ios 大版本号
   */

  var getIOSVersion = function getIOSVersion() {
    var version = navigator.appVersion.match(/OS (\d+)_(\d+)_?(\d+)?/);
    return Number.parseInt(version[1], 10);
  };
  /**
   * 获取 微信 版本号
   */

  var getWeChatVersion = function getWeChatVersion() {
    var version = navigator.appVersion.match(/micromessenger\/(\d+\.\d+\.\d+)/i);
    return version[1];
  };
  var isAndroid = /android/i.test(ua);
  var isIos = /iphone|ipad|ipod/i.test(ua);
  var isWechat = /micromessenger\/([\d.]+)/i.test(ua);
  var isWeibo = /(weibo).*weibo__([\d.]+)/i.test(ua);
  var isBaidu = /(baiduboxapp)\/([\d.]+)/i.test(ua);
  var isQQ = /qq\/([\d.]+)/i.test(ua);
  var isQQBrowser = /(qqbrowser)\/([\d.]+)/i.test(ua);
  var isQzone = /qzone\/.*_qz_([\d.]+)/i.test(ua); // 安卓 chrome 浏览器，包含 原生chrome浏览器、三星自带浏览器、360浏览器以及早期国内厂商自带浏览器

  var isOriginalChrome = /chrome\/[\d.]+ mobile safari\/[\d.]+/i.test(ua) && isAndroid && ua.indexOf('Version') < 0;

  // 根据 param 生成 queryString
  function generateQS(param) {
    var qs = typeof param !== 'undefined' ? Object.keys(param).map(function (key) {
      return "".concat(key, "=").concat(param[key]);
    }).join('&') : '';
    return qs ? "?".concat(qs) : '';
  } // 生成基本的 url scheme


  function buildScheme(config, options) {
    var path = config.path,
        param = config.param;
    var scheme = options.scheme,
        customBuildScheme = options.buildScheme;

    if (typeof customBuildScheme !== 'undefined') {
      return customBuildScheme(config, options);
    }

    var host = scheme.host,
        port = scheme.port,
        protocol = scheme.protocol;
    var portPart = port ? ":".concat(port) : '';
    var hostPort = host ? "".concat(host).concat(portPart, "/") : '';
    var qs = generateQS(param);
    return "".concat(protocol, "://").concat(hostPort).concat(path).concat(qs);
  } // 生成业务需要的 url scheme（区分是否是外链）

  function generateScheme(config, options) {
    var outChain = options.outChain;
    var uri = buildScheme(config, options);

    if (typeof outChain !== 'undefined' && outChain) {
      var protocol = outChain.protocol,
          path = outChain.path,
          key = outChain.key;
      uri = "".concat(protocol, "://").concat(path, "?").concat(key, "=").concat(encodeURIComponent(uri));
    }

    return uri;
  } // 生成 android intent

  function generateIntent(config, options) {
    var outChain = options.outChain;
    var intent = options.intent,
        fallback = options.fallback;
    if (typeof intent === 'undefined') return '';
    var keys = Object.keys(intent);
    var intentParam = keys.map(function (key) {
      return "".concat(key, "=").concat(intent[key], ";");
    }).join('');
    var intentTail = "#Intent;".concat(intentParam, "S.browser_fallback_url=").concat(encodeURIComponent(fallback), ";end;");
    var urlPath = buildScheme(config, options);

    if (typeof outChain !== 'undefined' && outChain) {
      var path = outChain.path,
          key = outChain.key;
      return "intent://".concat(path, "?").concat(key, "=").concat(encodeURIComponent(urlPath)).concat(intentTail);
    }

    urlPath = urlPath.slice(urlPath.indexOf('//') + 2);
    return "intent://".concat(urlPath).concat(intentTail);
  } // 生成 universalLink

  function generateUniversalLink(config, options) {
    var universal = options.universal;
    if (typeof universal === 'undefined') return '';
    var host = universal.host,
        pathKey = universal.pathKey;
    var path = config.path,
        param = config.param;
    var qs = generateQS(param);
    var newUniversalLink = "https://".concat(host, "/").concat(path).concat(qs);
    var oldUniversalLink = "https://".concat(host, "?").concat(pathKey, "=").concat(path).concat(qs.replace('?', '&'));
    return pathKey ? oldUniversalLink : newUniversalLink;
  } // 生成 应用宝链接

  function generateYingYongBao(config, options) {
    var url = generateScheme(config, options); // 支持 AppLink

    return "".concat(options.yingyongbao, "&android_schema=").concat(encodeURIComponent(url));
  }

  var hidden;
  var visibilityChange;
  var iframe;

  function getSupportedProperty() {
    if (typeof document === 'undefined') return;

    if (typeof document.hidden !== 'undefined') {
      // Opera 12.10 and Firefox 18 and later support
      hidden = 'hidden';
      visibilityChange = 'visibilitychange';
    } else if (typeof document.msHidden !== 'undefined') {
      hidden = 'msHidden';
      visibilityChange = 'msvisibilitychange';
    } else if (typeof document.webkitHidden !== 'undefined') {
      hidden = 'webkitHidden';
      visibilityChange = 'webkitvisibilitychange';
    }
  }

  getSupportedProperty();
  /**
   * 判断页面是否隐藏（进入后台）
   */

  function isPageHidden() {
    if (typeof hidden === 'undefined') return false;
    return document[hidden];
  }
  /**
   * 通过 top.location.href 跳转
   * @param {string}} [uri] - 需要打开的地址
   */


  function evokeByLocation(uri) {
    window.top.location.href = uri;
  }
  /**
   * 通过 A 标签唤起
   * @param {string} uri - 需要打开的地址
   */

  function evokeByTagA(uri) {
    var tagA = document.createElement('a');
    tagA.setAttribute('href', uri);
    tagA.style.display = 'none'; // append 在 android 6 系统中有兼容性问题
    // eslint-disable-next-line unicorn/prefer-node-append

    document.body.appendChild(tagA);
    tagA.click();
  }
  /**
   * 通过 iframe 唤起
   * @param {string} [uri] - 需要打开的地址
   */

  function evokeByIFrame(uri) {
    if (!iframe) {
      iframe = document.createElement('iframe');
      iframe.style.cssText = 'display:none;border:0;width:0;height:0;';
      document.body.appendChild(iframe);
    }

    iframe.src = uri;
  }
  /**
   * 检测是否唤端成功
   * @param cb - 唤端失败回调函数
   * @param timeout
   */

  function checkOpen(failure, timeout) {
    var timer = setTimeout(function () {
      var pageHidden = isPageHidden();

      if (!pageHidden) {
        failure();
      }
    }, timeout);

    if (typeof visibilityChange !== 'undefined') {
      document.addEventListener(visibilityChange, function () {
        clearTimeout(timer);
      });
    } else {
      window.addEventListener('pagehide', function () {
        clearTimeout(timer);
      });
    }
  }

  var CallApp = /*#__PURE__*/function () {
    // Create an instance of CallApp
    function CallApp(options) {
      _classCallCheck(this, CallApp);

      _defineProperty(this, "options", void 0);

      var defaultOptions = {
        timeout: 2000
      };
      this.options = _extends(defaultOptions, options);
    }
    /**
     * 注册为方法
     * generateScheme | generateIntent | generateUniversalLink | generateYingYongBao | checkOpen
     */


    _createClass(CallApp, [{
      key: "generateScheme",
      value: function generateScheme$1(config) {
        return generateScheme(config, this.options);
      }
    }, {
      key: "generateIntent",
      value: function generateIntent$1(config) {
        return generateIntent(config, this.options);
      }
    }, {
      key: "generateUniversalLink",
      value: function generateUniversalLink$1(config) {
        return generateUniversalLink(config, this.options);
      }
    }, {
      key: "generateYingYongBao",
      value: function generateYingYongBao$1(config) {
        return generateYingYongBao(config, this.options);
      }
    }, {
      key: "checkOpen",
      value: function checkOpen$1(failure) {
        var _this$options = this.options,
            logFunc = _this$options.logFunc,
            timeout = _this$options.timeout;
        return checkOpen(function () {
          if (typeof logFunc !== 'undefined') {
            logFunc('failure');
          }

          failure();
        }, timeout);
      } // 唤端失败跳转 app store

    }, {
      key: "fallToAppStore",
      value: function fallToAppStore() {
        var _this = this;

        this.checkOpen(function () {
          evokeByLocation(_this.options.appstore);
        });
      } // 唤端失败跳转通用(下载)页

    }, {
      key: "fallToFbUrl",
      value: function fallToFbUrl() {
        var _this2 = this;

        this.checkOpen(function () {
          evokeByLocation(_this2.options.fallback);
        });
      } // 唤端失败调用自定义回调函数

    }, {
      key: "fallToCustomCb",
      value: function fallToCustomCb(callback) {
        this.checkOpen(function () {
          callback();
        });
      }
      /**
       * 唤起客户端
       * 根据不同 browser 执行不同唤端策略
       */

    }, {
      key: "open",
      value: function open(config) {
        var _this$options2 = this.options,
            universal = _this$options2.universal,
            appstore = _this$options2.appstore,
            logFunc = _this$options2.logFunc,
            intent = _this$options2.intent;
        var callback = config.callback;
        var supportUniversal = typeof universal !== 'undefined';
        var schemeURL = this.generateScheme(config);
        var checkOpenFall;

        if (typeof logFunc !== 'undefined') {
          logFunc('pending');
        }

        var isSupportWeibo = !!this.options.isSupportWeibo;

        if (isIos) {
          // ios qq 禁止了 universalLink 唤起app，安卓不受影响 - 18年12月23日
          // ios qq 浏览器禁止了 universalLink - 19年5月1日
          // ios 微信自 7.0.5 版本放开了 Universal Link 的限制
          // ios 微博禁止了 universalLink
          if (isWechat && semverCompare(getWeChatVersion(), '7.0.5') === -1 || isWeibo && !isSupportWeibo) {
            evokeByLocation(appstore);
          } else if (getIOSVersion() < 9) {
            evokeByIFrame(schemeURL);
            checkOpenFall = this.fallToAppStore;
          } else if (!supportUniversal || isQQ || isQQBrowser || isQzone) {
            evokeByTagA(schemeURL);
            checkOpenFall = this.fallToAppStore;
          } else {
            evokeByLocation(this.generateUniversalLink(config));
          } // Android
          // 在微信中且配置了应用宝链接

        } else if (isWechat && typeof this.options.yingyongbao !== 'undefined') {
          evokeByLocation(this.generateYingYongBao(config));
        } else if (isOriginalChrome) {
          if (typeof intent !== 'undefined') {
            evokeByLocation(this.generateIntent(config));
          } else {
            // scheme 在 andriod chrome 25+ 版本上iframe无法正常拉起
            evokeByLocation(schemeURL);
            checkOpenFall = this.fallToFbUrl;
          }
        } else if (isWechat || isBaidu || isWeibo && !isSupportWeibo || isQzone) {
          evokeByLocation(this.options.fallback);
        } else {
          evokeByIFrame(schemeURL);
          checkOpenFall = this.fallToFbUrl;
        }

        if (typeof callback !== 'undefined') {
          this.fallToCustomCb(callback);
          return;
        }

        if (!checkOpenFall) return;
        checkOpenFall.call(this);
      }
    }]);

    return CallApp;
  }();

  return CallApp;

})));
