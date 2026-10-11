import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Bell, 
  Send, 
  CheckCircle2, 
  AlertTriangle, 
  Info, 
  RefreshCw, 
  Trash2, 
  Plus, 
  Search, 
  Sliders, 
  Sparkles, 
  ShieldCheck, 
  ShieldAlert, 
  Globe, 
  TrendingUp, 
  ArrowUpRight, 
  ArrowDownRight, 
  Clock, 
  HelpCircle, 
  Check, 
  X,
  MessageSquare,
  Smartphone,
  Layers,
  BrainCircuit,
  Newspaper
} from 'lucide-react';
import { 
  NotificationSettings, 
  PriceAlertRule, 
  DeliveryLog 
} from '../types';
import { api } from '../services/api';

export const NotificationCenterView: React.FC = () => {
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [priceRules, setPriceRules] = useState<PriceAlertRule[]>([]);
  const [deliveryLogs, setDeliveryLogs] = useState<DeliveryLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Channel Testing State
  const [testingChannel, setTestingChannel] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { success: boolean; message: string }>>({});

  // Telegram Configuration Modal State
  const [showTelegramConfigModal, setShowTelegramConfigModal] = useState<boolean>(false);
  const [telegramBotTokenInput, setTelegramBotTokenInput] = useState<string>('');
  const [telegramChatIdInput, setTelegramChatIdInput] = useState<string>('');
  const [configuringTelegram, setConfiguringTelegram] = useState<boolean>(false);
  const [telegramConfigError, setTelegramConfigError] = useState<string | null>(null);

  // WhatsApp Configuration Modal State
  const [showWhatsAppConfigModal, setShowWhatsAppConfigModal] = useState<boolean>(false);
  const [whatsappTokenInput, setWhatsappTokenInput] = useState<string>('');
  const [whatsappPhoneIdInput, setWhatsappPhoneIdInput] = useState<string>('');
  const [whatsappRecipientInput, setWhatsappRecipientInput] = useState<string>('');
  const [configuringWhatsApp, setConfiguringWhatsApp] = useState<boolean>(false);
  const [whatsappConfigError, setWhatsappConfigError] = useState<string | null>(null);

  // Coin selection search filter
  const [coinSearch, setCoinSearch] = useState<string>('');

  // Price Rule Creation Modal / Form State
  const [showRuleModal, setShowRuleModal] = useState<boolean>(false);
  const [newRuleSymbol, setNewRuleSymbol] = useState<string>('BTCUSDT');
  const [newRuleCondition, setNewRuleCondition] = useState<'entering_range' | 'exiting_range' | 'crossing_up' | 'crossing_down'>('entering_range');
  const [newRuleLower, setNewRuleLower] = useState<string>('60000');
  const [newRuleUpper, setNewRuleUpper] = useState<string>('65000');
  const [newRuleTarget, setNewRuleTarget] = useState<string>('65000');
  const [newRuleChannels, setNewRuleChannels] = useState<{ in_app: boolean; telegram: boolean; whatsapp: boolean }>({
    in_app: true,
    telegram: true,
    whatsapp: false
  });
  const [creatingRule, setCreatingRule] = useState<boolean>(false);

  // Instructions Modals
  const [showTelegramGuide, setShowTelegramGuide] = useState<boolean>(false);
  const [showWhatsAppGuide, setShowWhatsAppGuide] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [s, rules, logs] = await Promise.all([
        api.getNotificationSettings(),
        api.getPriceRules(),
        api.getDeliveryHistory(20)
      ]);
      setSettings(s);
      setPriceRules(rules);
      setDeliveryLogs(logs);
    } catch (e: any) {
      console.error('Failed to load notification settings:', e);
      setBanner({ type: 'error', message: e?.message || 'Failed to load notification center data.' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Update Settings Helper
  const handleSaveSettings = async (partial: Partial<NotificationSettings>) => {
    if (!settings) return;
    setSaving(true);
    setBanner(null);
    try {
      await api.updateNotificationSettings(partial);
      const updated = await api.getNotificationSettings();
      setSettings(updated);
      setBanner({ type: 'success', message: 'Notification preferences saved successfully!' });
    } catch (e: any) {
      console.error('Failed to update settings:', e);
      setBanner({ type: 'error', message: e?.message || 'Failed to update preferences.' });
    } finally {
      setSaving(false);
    }
  };

  // Channel Configuration Handlers
  const handleConfigureTelegram = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!telegramBotTokenInput.trim()) {
      setTelegramConfigError('Telegram Bot Token is required.');
      return;
    }
    setConfiguringTelegram(true);
    setTelegramConfigError(null);
    try {
      const res = await api.configureTelegram({
        bot_token: telegramBotTokenInput.trim(),
        chat_id: telegramChatIdInput.trim() || undefined,
        save_to_local_env: true
      });
      setBanner({ type: 'success', message: res.message || 'Telegram Bot verified and connected successfully!' });
      setShowTelegramConfigModal(false);
      setTelegramBotTokenInput('');
      setTelegramChatIdInput('');
      const updated = await api.getNotificationSettings();
      setSettings(updated);
    } catch (e: any) {
      setTelegramConfigError(e?.message || 'Telegram verification failed.');
    } finally {
      setConfiguringTelegram(false);
    }
  };

  const handleConfigureWhatsApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whatsappTokenInput.trim() || !whatsappPhoneIdInput.trim()) {
      setWhatsappConfigError('WhatsApp API Token and Phone Number ID are required.');
      return;
    }
    setConfiguringWhatsApp(true);
    setWhatsappConfigError(null);
    try {
      const res = await api.configureWhatsApp({
        api_token: whatsappTokenInput.trim(),
        phone_number_id: whatsappPhoneIdInput.trim(),
        recipient_phone: whatsappRecipientInput.trim() || undefined,
        save_to_local_env: true
      });
      setBanner({ type: 'success', message: res.message || 'Meta WhatsApp credentials verified and connected successfully!' });
      setShowWhatsAppConfigModal(false);
      setWhatsappTokenInput('');
      setWhatsappPhoneIdInput('');
      setWhatsappRecipientInput('');
      const updated = await api.getNotificationSettings();
      setSettings(updated);
    } catch (e: any) {
      setWhatsappConfigError(e?.message || 'WhatsApp verification failed.');
    } finally {
      setConfiguringWhatsApp(false);
    }
  };

  // Test Channel Action
  const handleTestChannel = async (channel: string) => {
    setTestingChannel(channel);
    try {
      const res = await api.testNotification(channel);
      setTestResult(prev => ({
        ...prev,
        [channel]: {
          success: res.success,
          message: res.message
        }
      }));
      // Immediately refresh settings & delivery history to sync status
      const [updatedSettings, updatedLogs] = await Promise.all([
        api.getNotificationSettings(),
        api.getDeliveryHistory(20)
      ]);
      setSettings(updatedSettings);
      setDeliveryLogs(updatedLogs);
    } catch (e: any) {
      setTestResult(prev => ({
        ...prev,
        [channel]: {
          success: false,
          message: e?.message || `Failed to test ${channel}.`
        }
      }));
      api.getNotificationSettings().then(setSettings).catch(() => {});
    } finally {
      setTestingChannel(null);
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'CONNECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/90 text-emerald-300 border border-emerald-700/80 shadow-sm shadow-emerald-950/40">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>CONNECTED</span>
          </span>
        );
      case 'VALIDATING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-cyan-950/90 text-cyan-300 border border-cyan-700/80">
            <RefreshCw className="w-3 h-3 text-cyan-400 animate-spin" />
            <span>VALIDATING</span>
          </span>
        );
      case 'INVALID_CREDENTIALS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-950/90 text-rose-300 border border-rose-700/80">
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            <span>INVALID CREDENTIALS</span>
          </span>
        );
      case 'CONFIGURATION_ERROR':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-950/90 text-amber-300 border border-amber-700/80">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span>CONFIG ERROR</span>
          </span>
        );
      case 'PROVIDER_UNAVAILABLE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-orange-950/90 text-orange-300 border border-orange-700/80">
            <AlertTriangle className="w-3 h-3 text-orange-400" />
            <span>PROVIDER UNAVAILABLE</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
            <span>NOT CONFIGURED</span>
          </span>
        );
    }
  };

  // Price Rule Actions
  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingRule(true);
    setBanner(null);

    try {
      const channelsStr = Object.entries(newRuleChannels)
        .filter(([_, enabled]) => enabled)
        .map(([ch]) => ch)
        .join(',');

      const payload: any = {
        symbol: newRuleSymbol,
        condition_type: newRuleCondition,
        channels: channelsStr || 'in_app'
      };

      if (newRuleCondition === 'entering_range' || newRuleCondition === 'exiting_range') {
        const lower = parseFloat(newRuleLower);
        const upper = parseFloat(newRuleUpper);
        if (isNaN(lower) || isNaN(upper) || lower <= 0 || upper <= 0) {
          throw new Error('Please enter valid positive numbers for price boundaries.');
        }
        if (lower >= upper) {
          throw new Error('Lower price boundary must be strictly lower than upper boundary.');
        }
        payload.lower_boundary = lower;
        payload.upper_boundary = upper;
      } else {
        const target = parseFloat(newRuleTarget);
        if (isNaN(target) || target <= 0) {
          throw new Error('Please enter a valid positive target price.');
        }
        payload.target_price = target;
      }

      const created = await api.createPriceRule(payload);
      setPriceRules(prev => [created, ...prev]);
      setShowRuleModal(false);
      setBanner({ type: 'success', message: `Price alert rule created for ${newRuleSymbol}!` });
    } catch (e: any) {
      setBanner({ type: 'error', message: e?.message || 'Failed to create price alert rule.' });
    } finally {
      setCreatingRule(false);
    }
  };

  const handleToggleRule = async (id: string, currentActive: boolean) => {
    try {
      await api.updatePriceRule(id, !currentActive);
      setPriceRules(prev => prev.map(r => r.id === id ? { ...r, is_active: !currentActive } : r));
    } catch (e: any) {
      setBanner({ type: 'error', message: e?.message || 'Failed to update rule status.' });
    }
  };

  const handleDeleteRule = async (id: string) => {
    if (!window.confirm('Delete this price alert rule?')) return;
    try {
      await api.deletePriceRule(id);
      setPriceRules(prev => prev.filter(r => r.id !== id));
      setBanner({ type: 'success', message: 'Price rule removed.' });
    } catch (e: any) {
      setBanner({ type: 'error', message: e?.message || 'Failed to delete rule.' });
    }
  };

  const handleTriggerSummary = async () => {
    try {
      await api.triggerSummaryNow();
      setBanner({ type: 'success', message: 'Test market summary dispatched to active channels!' });
      api.getDeliveryHistory(20).then(setDeliveryLogs);
    } catch (e: any) {
      setBanner({ type: 'error', message: e?.message || 'Failed to trigger summary.' });
    }
  };

  // Filtered symbols list for coin selection
  const availableCoins = settings?.available_symbols || [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT',
    'LTCUSDT', 'BCHUSDT', 'TRXUSDT', 'ARBUSDT', 'SUIUSDT',
    'APTUSDT', 'NEARUSDT', 'UNIUSDT', 'ETCUSDT', 'FILUSDT'
  ];

  const filteredCoins = useMemo(() => {
    if (!coinSearch.trim()) return availableCoins;
    const q = coinSearch.toUpperCase().trim();
    return availableCoins.filter(c => c.includes(q));
  }, [availableCoins, coinSearch]);

  if (loading && !settings) {
    return (
      <div className="py-24 text-center text-slate-500 font-mono text-xs">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3 text-cyan-400" />
        <p>Loading Notification Center...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      
      {/* Top Banner Notice */}
      {banner && (
        <div className={`p-4 rounded-xl border flex items-start gap-3 text-xs transition-all ${
          banner.type === 'success'
            ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
            : 'bg-rose-950/60 border-rose-800 text-rose-300'
        }`}>
          {banner.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p className="font-semibold">{banner.message}</p>
          </div>
          <button onClick={() => setBanner(null)} className="text-slate-400 hover:text-slate-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Header Summary */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-cyan-400 flex items-center justify-center text-white shadow-lg shadow-cyan-950/50">
              <Bell className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
                NOTIFICATION CENTER & ALERT DISPATCHER
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Multi-channel alert routing across Telegram, WhatsApp, and Persistent In-App Notifications
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerSummary}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            Dispatch Test Summary Now
          </button>
          <button
            onClick={loadData}
            title="Reload notification data"
            className="p-2 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded-xl transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* SECTION 1: DELIVERY CHANNELS */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2 font-mono">
            <Smartphone className="w-4 h-4 text-cyan-400" />
            <span>1. Delivery Channels Configuration</span>
          </h3>
          <span className="text-[11px] text-slate-500 font-mono">Simultaneous Multi-Channel Active</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          
          {/* Channel A: Telegram */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-lg flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-400">
                    <Send className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-slate-100">Telegram Bot</h4>
                    <span className="text-[10px] font-mono text-slate-500">Official Telegram Bot API</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings?.telegram_enabled || false}
                      onChange={(e) => handleSaveSettings({ telegram_enabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-600"></div>
                  </label>
                </div>
              </div>

              {/* Status Header Pill */}
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400 font-semibold">Connection Status:</span>
                {renderStatusBadge(settings?.telegram_status || (settings?.telegram_verified ? 'CONNECTED' : 'NOT_CONFIGURED'))}
              </div>

              {/* Status & Inputs Details */}
              <div className="space-y-2.5 text-xs font-mono bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Recipient Chat ID:</span>
                  <span className="text-slate-200 font-semibold">{settings?.telegram_chat_id_masked || 'Not Set'}</span>
                </div>

                {settings?.telegram_sender_info && (
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Linked Bot:</span>
                    <span className="text-cyan-400 font-bold truncate max-w-[170px]" title={settings.telegram_sender_info}>
                      {settings.telegram_sender_info}
                    </span>
                  </div>
                )}

                {settings?.telegram_verified_at && (
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span>Verified At:</span>
                    <span>{new Date(settings.telegram_verified_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  </div>
                )}

                {settings?.telegram_last_delivery && (
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span>Last Sent:</span>
                    <span>{new Date(settings.telegram_last_delivery).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                )}

                {settings?.telegram_last_error && (
                  <div className="pt-1.5 border-t border-slate-850">
                    <p className="text-[10px] text-rose-400 line-clamp-2 leading-tight">
                      {settings.telegram_last_error}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
              <button
                onClick={() => {
                  setTelegramConfigError(null);
                  setShowTelegramConfigModal(true);
                }}
                className="w-full py-2 bg-cyan-950/40 hover:bg-cyan-900/60 text-cyan-300 text-xs font-mono font-semibold rounded-xl border border-cyan-800/60 transition-colors flex items-center justify-center gap-1.5"
              >
                <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                <span>Configure Telegram Bot</span>
              </button>

              <button
                onClick={() => handleTestChannel('telegram')}
                disabled={testingChannel === 'telegram'}
                className="w-full py-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-mono font-semibold rounded-xl border border-slate-700/80 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testingChannel === 'telegram' ? 'animate-spin text-cyan-400' : ''}`} />
                <span>Test Telegram Message</span>
              </button>

              {testResult.telegram && (
                <p className={`text-[10px] font-mono mt-1 text-center ${testResult.telegram.success ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {testResult.telegram.message}
                </p>
              )}
            </div>
          </div>

          {/* Channel B: WhatsApp */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-lg flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-emerald-950 border border-emerald-800 text-emerald-400">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-slate-100">WhatsApp Business</h4>
                    <span className="text-[10px] font-mono text-slate-500">Official Meta Cloud API</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings?.whatsapp_enabled || false}
                      onChange={(e) => handleSaveSettings({ whatsapp_enabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>
              </div>

              {/* Status Header Pill */}
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400 font-semibold">Connection Status:</span>
                {renderStatusBadge(settings?.whatsapp_status || (settings?.whatsapp_verified ? 'CONNECTED' : 'NOT_CONFIGURED'))}
              </div>

              {/* Status Details */}
              <div className="space-y-2.5 text-xs font-mono bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Phone ID:</span>
                  <span className="text-slate-200 font-semibold">{settings?.whatsapp_phone_number_id_masked || 'Not Configured'}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Recipient (E.164):</span>
                  <span className="text-slate-200 font-semibold">{settings?.whatsapp_phone_number_masked || 'Not Set'}</span>
                </div>

                {settings?.whatsapp_sender_info && (
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Verified Sender:</span>
                    <span className="text-emerald-400 font-bold truncate max-w-[160px]" title={settings.whatsapp_sender_info}>
                      {settings.whatsapp_sender_info}
                    </span>
                  </div>
                )}

                {settings?.whatsapp_verified_at && (
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span>Verified At:</span>
                    <span>{new Date(settings.whatsapp_verified_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  </div>
                )}

                {settings?.whatsapp_last_delivery && (
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span>Last Sent:</span>
                    <span>{new Date(settings.whatsapp_last_delivery).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                )}

                {settings?.whatsapp_last_error && (
                  <div className="pt-1.5 border-t border-slate-850">
                    <p className="text-[10px] text-rose-400 line-clamp-2 leading-tight">
                      {settings.whatsapp_last_error}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
              <button
                onClick={() => {
                  setWhatsappConfigError(null);
                  setShowWhatsAppConfigModal(true);
                }}
                className="w-full py-2 bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-mono font-semibold rounded-xl border border-emerald-800/60 transition-colors flex items-center justify-center gap-1.5"
              >
                <Sliders className="w-3.5 h-3.5 text-emerald-400" />
                <span>Configure WhatsApp Credentials</span>
              </button>

              <button
                onClick={() => handleTestChannel('whatsapp')}
                disabled={testingChannel === 'whatsapp'}
                className="w-full py-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-mono font-semibold rounded-xl border border-slate-700/80 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testingChannel === 'whatsapp' ? 'animate-spin text-emerald-400' : ''}`} />
                <span>Test WhatsApp Message</span>
              </button>

              {testResult.whatsapp && (
                <p className={`text-[10px] font-mono mt-1 text-center ${testResult.whatsapp.success ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {testResult.whatsapp.message}
                </p>
              )}
            </div>
          </div>

          {/* Channel C: In-App Notifications */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-lg flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-indigo-950 border border-indigo-800 text-indigo-400">
                    <Bell className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-slate-100">In-App Notifications</h4>
                    <span className="text-[10px] font-mono text-slate-500">Persistent Relational Store</span>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings?.in_app_enabled ?? true}
                    onChange={(e) => handleSaveSettings({ in_app_enabled: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>

              {/* Status Header Pill */}
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400 font-semibold">Connection Status:</span>
                {renderStatusBadge(settings?.in_app_status || 'CONNECTED')}
              </div>

              <div className="space-y-2.5 text-xs font-mono bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Header Alert Drawer:</span>
                  <span className="text-emerald-400 font-bold">READY</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Storage Backend:</span>
                  <span className="text-slate-300">Database Engine</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Real-Time Sync:</span>
                  <span className="text-indigo-400 font-bold">WebSockets</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
              <button
                onClick={() => handleTestChannel('in_app')}
                disabled={testingChannel === 'in_app'}
                className="w-full py-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-mono font-semibold rounded-xl border border-slate-700/80 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testingChannel === 'in_app' ? 'animate-spin text-indigo-400' : ''}`} />
                <span>Generate In-App Test Alert</span>
              </button>

              {testResult.in_app && (
                <p className={`text-[10px] font-mono mt-1 text-center ${testResult.in_app.success ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {testResult.in_app.message}
                </p>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* SECTION 2: COIN SELECTION */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2 font-mono">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span>2. Market Coin Universe & Instrument Filter</span>
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Configure alerts for all {availableCoins.length} Binance USDⓈ-M Futures pairs or a selected subset.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-mono">
              <input
                type="radio"
                name="coin_mode"
                checked={settings?.all_coins || false}
                onChange={() => handleSaveSettings({ all_coins: true })}
                className="text-cyan-600 focus:ring-cyan-500 bg-slate-950 border-slate-700"
              />
              <span className="font-semibold text-slate-200">All Supported Coins ({availableCoins.length})</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-xs font-mono">
              <input
                type="radio"
                name="coin_mode"
                checked={!settings?.all_coins}
                onChange={() => handleSaveSettings({ all_coins: false })}
                className="text-cyan-600 focus:ring-cyan-500 bg-slate-950 border-slate-700"
              />
              <span className="font-semibold text-slate-200">Custom Selection</span>
            </label>
          </div>
        </div>

        {/* Custom Coin Selection Grid */}
        {!settings?.all_coins && (
          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between gap-3">
              <div className="relative flex-1 max-w-xs">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={coinSearch}
                  onChange={(e) => setCoinSearch(e.target.value)}
                  placeholder="Search symbols (e.g. BTC, SOL)..."
                  className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center gap-2 text-xs font-mono">
                <button
                  onClick={() => handleSaveSettings({ selected_coins: availableCoins })}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300"
                >
                  Select All
                </button>
                <button
                  onClick={() => handleSaveSettings({ selected_coins: [] })}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300"
                >
                  Clear All
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2 max-h-48 overflow-y-auto p-2 bg-slate-950/60 rounded-xl border border-slate-850">
              {filteredCoins.map(sym => {
                const selected = settings?.selected_coins?.includes(sym);
                return (
                  <button
                    key={sym}
                    onClick={() => {
                      const cur = settings?.selected_coins || [];
                      const updated = selected ? cur.filter(c => c !== sym) : [...cur, sym];
                      handleSaveSettings({ selected_coins: updated });
                    }}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition-colors ${
                      selected
                        ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                        : 'bg-slate-900/60 text-slate-500 hover:text-slate-300 border border-transparent'
                    }`}
                  >
                    <span>{sym.replace('USDT', '')}</span>
                    {selected && <Check className="w-3 h-3 text-cyan-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* SECTION 3: ML SIGNAL ALERTS */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2 font-mono">
              <BrainCircuit className="w-4 h-4 text-cyan-400" />
              <span>3. User-Configurable ML Signal Alerts</span>
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Set minimum confidence thresholds (e.g. 60%, 75%, 90%), statistical edge, and direction filters.
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings?.ml_alerts_enabled || false}
              onChange={(e) => handleSaveSettings({ ml_alerts_enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-600"></div>
          </label>
        </div>

        {/* Confidence Threshold Slider & Input */}
        <div className="space-y-3 bg-slate-950/70 p-5 rounded-2xl border border-slate-850">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">
                Minimum ML Prediction Confidence Threshold
              </span>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                Signals below this calibrated threshold will be silently filtered out.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-black font-mono text-cyan-400">
                {Math.round((settings?.ml_min_confidence || 0.60) * 100)}%
              </span>
            </div>
          </div>

          {/* Interactive Range Slider */}
          <input
            type="range"
            min="0"
            max="100"
            step="1"
            value={Math.round((settings?.ml_min_confidence || 0.60) * 100)}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10) / 100;
              setSettings(prev => prev ? { ...prev, ml_min_confidence: val } : null);
            }}
            onMouseUp={(e: any) => {
              const val = parseInt(e.target.value, 10) / 100;
              handleSaveSettings({ ml_min_confidence: val });
            }}
            className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />

          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
            <span>0% (All Signals)</span>
            <span className="text-slate-400">60% (Moderate Confidence)</span>
            <span className="text-cyan-400 font-bold">75% (High Conviction)</span>
            <span className="text-indigo-400 font-bold">90% (Strict Elite)</span>
            <span>100% (Maximum)</span>
          </div>
        </div>

        {/* Direction & Timeframe Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs font-mono">
          {/* Directions */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5">
            <span className="text-slate-400 font-bold block uppercase text-[11px]">
              Allowed Signal Directions:
            </span>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings?.ml_notify_buy || false}
                  onChange={(e) => handleSaveSettings({ ml_notify_buy: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500"
                />
                <span className="font-bold text-emerald-400">BUY / LONG</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings?.ml_notify_sell || false}
                  onChange={(e) => handleSaveSettings({ ml_notify_sell: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-rose-500 focus:ring-rose-500"
                />
                <span className="font-bold text-rose-400">SELL / SHORT</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings?.ml_notify_neutral || false}
                  onChange={(e) => handleSaveSettings({ ml_notify_neutral: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-slate-500 focus:ring-slate-500"
                />
                <span className="text-slate-400">NEUTRAL</span>
              </label>
            </div>
          </div>

          {/* Timeframes */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5">
            <span className="text-slate-400 font-bold block uppercase text-[11px]">
              Model Timeframes:
            </span>
            <div className="flex items-center gap-2">
              {['1h', '5m', '4h'].map(tf => {
                const active = settings?.ml_timeframes?.includes(tf);
                return (
                  <button
                    key={tf}
                    onClick={() => {
                      const cur = settings?.ml_timeframes || [];
                      const updated = active ? cur.filter(t => t !== tf) : [...cur, tf];
                      handleSaveSettings({ ml_timeframes: updated });
                    }}
                    className={`px-3 py-1 rounded-lg font-bold ${
                      active ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-slate-900 text-slate-500'
                    }`}
                  >
                    {tf.toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Safety Indicator */}
        <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-900/40 text-[11px] font-mono text-cyan-300 flex items-center gap-2">
          <Sparkles className="w-4 h-4 shrink-0" />
          <span>Informational predictive intelligence only. Notifications never place real orders or alter trading positions.</span>
        </div>
      </div>

      {/* SECTION 4: PRICE-RANGE AND PRICE-CROSSING ALERTS */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2 font-mono">
              <TrendingUp className="w-4 h-4 text-amber-400" />
              <span>4. Price-Range & Price-Crossing Rules</span>
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Independent price boundary monitors evaluated in real time against live market feeds.
            </p>
          </div>

          <button
            onClick={() => setShowRuleModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-slate-950 font-bold text-xs rounded-xl shadow-md transition-all font-mono"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Price Rule</span>
          </button>
        </div>

        {/* Active Rules List */}
        {priceRules.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
            <TrendingUp className="w-8 h-8 mx-auto mb-2 text-slate-700 stroke-1" />
            <p className="text-slate-400 font-medium">No price rules configured</p>
            <p className="text-[11px] text-slate-600 mt-1">Create a rule above to receive alerts when prices cross boundaries.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] text-slate-500 uppercase">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Condition</th>
                  <th className="py-2.5 px-3">Boundaries / Target</th>
                  <th className="py-2.5 px-3">Channels</th>
                  <th className="py-2.5 px-3">Last State</th>
                  <th className="py-2.5 px-3">Active</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {priceRules.map(r => (
                  <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-3 font-bold text-slate-200">{r.symbol}</td>
                    <td className="py-3 px-3 text-slate-300">
                      <span className="capitalize">{r.condition_type.replace('_', ' ')}</span>
                    </td>
                    <td className="py-3 px-3 font-black text-cyan-400">
                      {r.condition_type.includes('range') ? (
                        <span>${r.lower_boundary?.toLocaleString()} - ${r.upper_boundary?.toLocaleString()} USDT</span>
                      ) : (
                        <span>${r.target_price?.toLocaleString()} USDT</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-400 uppercase">
                      {r.channels}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                        {r.last_state || 'WAITING'}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <button
                        onClick={() => handleToggleRule(r.id, r.is_active)}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          r.is_active ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-850 text-slate-500'
                        }`}
                      >
                        {r.is_active ? 'ENABLED' : 'PAUSED'}
                      </button>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleDeleteRule(r.id)}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/50 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SECTION 5: MARKET NEWS ALERTS */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2 font-mono">
              <Newspaper className="w-4 h-4 text-indigo-400" />
              <span>5. Market News Intelligence Alerts</span>
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Instant alerts for breaking cryptocurrency news from Cointelegraph, CoinDesk & Decrypt.
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings?.news_alerts_enabled || false}
              onChange={(e) => handleSaveSettings({ news_alerts_enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
          </label>
        </div>

        {/* Category Toggles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          {[
            { id: 'all', label: 'All Breaking News' },
            { id: 'bitcoin', label: 'Bitcoin & ETFs' },
            { id: 'ethereum', label: 'Ethereum & L2s' },
            { id: 'altcoins', label: 'Altcoins' },
            { id: 'regulation', label: 'SEC / CFTC Regulation' },
            { id: 'macro', label: 'Fed Macro & CPI' },
            { id: 'exchanges', label: 'Binance & CEXs' },
            { id: 'defi', label: 'DeFi & Web3' }
          ].map(cat => {
            const active = settings?.news_categories?.includes(cat.id);
            return (
              <button
                key={cat.id}
                onClick={() => {
                  const cur = settings?.news_categories || [];
                  const updated = active ? cur.filter(c => c !== cat.id) : [...cur, cat.id];
                  handleSaveSettings({ news_categories: updated });
                }}
                className={`p-3 rounded-xl border text-left font-semibold transition-all ${
                  active
                    ? 'bg-indigo-950/70 text-indigo-300 border-indigo-800'
                    : 'bg-slate-950/60 text-slate-500 border-slate-850 hover:text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>{cat.label}</span>
                  {active && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* SECTION 6: RISK AND SYSTEM ALERTS */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2 font-mono">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <span>6. Institutional Risk & Guardian Alerts</span>
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Receive immediate alerts when risk circuit breakers or hard portfolio stops engage.
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings?.risk_alerts_enabled || false}
              onChange={(e) => handleSaveSettings({ risk_alerts_enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-600"></div>
          </label>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs font-mono">
          {[
            { key: 'notify_circuit_breaker', label: 'Emergency Kill Switch / Breaker' },
            { key: 'notify_daily_loss', label: 'Max Daily Loss Limit (> 2.0%)' },
            { key: 'notify_drawdown', label: 'Trailing Drawdown Limit (> 10.0%)' },
            { key: 'notify_consecutive_losses', label: 'Consecutive Loss Streak (3 Trades)' },
            { key: 'notify_service_health', label: 'Market Feed / WebSocket Outage' }
          ].map(r => {
            const active = (settings as any)?.[r.key] || false;
            return (
              <label
                key={r.key}
                className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={active}
                  onChange={(e) => handleSaveSettings({ [r.key]: e.target.checked } as any)}
                  className="rounded border-slate-700 bg-slate-900 text-rose-500 focus:ring-rose-500"
                />
                <span className="text-slate-300 font-medium">{r.label}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* SECTION 7: DELIVERY AUDIT HISTORY */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h3 className="font-bold text-slate-100 text-sm font-mono uppercase">7. Delivery History Audit Log</h3>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Last 20 Dispatch Attempts</span>
        </div>

        {deliveryLogs.length === 0 ? (
          <p className="py-6 text-center text-slate-500 font-mono text-xs">No delivery attempts recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] text-slate-500 uppercase">
                  <th className="py-2 px-3">Timestamp</th>
                  <th className="py-2 px-3">Channel</th>
                  <th className="py-2 px-3">Category</th>
                  <th className="py-2 px-3">Recipient</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {deliveryLogs.map(l => (
                  <tr key={l.id} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      {new Date(l.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-2.5 px-3 font-bold text-slate-200 uppercase">{l.channel}</td>
                    <td className="py-2.5 px-3 text-slate-400">{l.category}</td>
                    <td className="py-2.5 px-3 text-slate-300">{l.recipient}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        l.status === 'DELIVERED'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : l.status === 'SKIPPED'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-rose-950 text-rose-400 border border-rose-800'
                      }`}>
                        {l.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px] max-w-xs truncate">
                      {l.error_message || l.payload_preview}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CREATE PRICE RULE MODAL */}
      {showRuleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm font-mono flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-400" />
                <span>Create Price Alert Rule</span>
              </h3>
              <button onClick={() => setShowRuleModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRule} className="space-y-4 text-xs font-mono">
              <div>
                <label className="block text-slate-300 mb-1">Target Instrument:</label>
                <select
                  value={newRuleSymbol}
                  onChange={(e) => setNewRuleSymbol(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200"
                >
                  {availableCoins.map(sym => (
                    <option key={sym} value={sym}>{sym}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Condition Type:</label>
                <select
                  value={newRuleCondition}
                  onChange={(e: any) => setNewRuleCondition(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200"
                >
                  <option value="entering_range">Entering Price Corridor</option>
                  <option value="exiting_range">Exiting Price Corridor (Breakout)</option>
                  <option value="crossing_up">Crossing Upward Past Price</option>
                  <option value="crossing_down">Crossing Downward Past Price</option>
                </select>
              </div>

              {newRuleCondition.includes('range') ? (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 mb-1">Lower Boundary ($):</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={newRuleLower}
                      onChange={(e) => setNewRuleLower(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 mb-1">Upper Boundary ($):</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={newRuleUpper}
                      onChange={(e) => setNewRuleUpper(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-slate-300 mb-1">Target Crossing Price ($):</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={newRuleTarget}
                    onChange={(e) => setNewRuleTarget(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200"
                  />
                </div>
              )}

              <div>
                <label className="block text-slate-300 mb-1">Channels to Alert:</label>
                <div className="flex items-center gap-3 pt-1">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newRuleChannels.in_app}
                      onChange={(e) => setNewRuleChannels(prev => ({ ...prev, in_app: e.target.checked }))}
                    />
                    <span>In-App</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newRuleChannels.telegram}
                      onChange={(e) => setNewRuleChannels(prev => ({ ...prev, telegram: e.target.checked }))}
                    />
                    <span>Telegram</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newRuleChannels.whatsapp}
                      onChange={(e) => setNewRuleChannels(prev => ({ ...prev, whatsapp: e.target.checked }))}
                    />
                    <span>WhatsApp</span>
                  </label>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowRuleModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-800 text-slate-400"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingRule}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-xl"
                >
                  {creatingRule ? 'Creating...' : 'Create Alert Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TELEGRAM SETUP GUIDE MODAL */}
      {showTelegramGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm flex items-center gap-2">
                <Send className="w-4 h-4 text-cyan-400" />
                <span>How to Link Telegram Bot</span>
              </h3>
              <button onClick={() => setShowTelegramGuide(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-slate-300 leading-relaxed font-sans">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <strong className="text-cyan-400 font-mono block">Step 1: Obtain your Telegram Chat ID</strong>
                <p className="text-slate-400 text-xs">
                  Open Telegram and search for <code>@userinfobot</code> or <code>@raw_data_bot</code>. Click Start, and the bot will reply with your numeric <strong>Id</strong> (e.g. <code>123456789</code>).
                </p>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <strong className="text-cyan-400 font-mono block">Step 2: Message your Bot</strong>
                <p className="text-slate-400 text-xs">
                  Telegram bots cannot send unsolicited messages to users first. Search for your configured bot username in Telegram and send a message (like <code>/start</code> or <code>hello</code>) so the bot has permission to message you.
                </p>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <strong className="text-cyan-400 font-mono block">Step 3: Test Delivery</strong>
                <p className="text-slate-400 text-xs">
                  Paste your numeric Chat ID into the Telegram card and click <strong>Test Telegram Message</strong>.
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowTelegramGuide(false)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl mt-2"
            >
              Understood
            </button>
          </div>
        </div>
      )}

      {/* WHATSAPP SETUP GUIDE MODAL */}
      {showWhatsAppGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" />
                <span>WhatsApp Business Setup & Provider Info</span>
              </h3>
              <button onClick={() => setShowWhatsAppGuide(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-slate-300 leading-relaxed font-sans">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <strong className="text-emerald-400 font-mono block">Supported Providers</strong>
                <p className="text-slate-400 text-xs">
                  We use official <strong>Meta WhatsApp Cloud API</strong> or <strong>Twilio WhatsApp API</strong>. We do NOT use unofficial web scrapers that get accounts banned.
                </p>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <strong className="text-emerald-400 font-mono block">Required Server Environment Variables</strong>
                <p className="text-slate-400 text-xs font-mono">
                  WHATSAPP_API_TOKEN=&lt;Meta_System_User_Token&gt;<br />
                  WHATSAPP_PHONE_NUMBER_ID=&lt;Phone_Number_ID&gt;<br />
                  WHATSAPP_ENABLED=true
                </p>
              </div>

              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <strong className="text-emerald-400 font-mono block">Recipient Number Format</strong>
                <p className="text-slate-400 text-xs">
                  Enter your number in standard international E.164 format including country code, e.g. <code>+14155552671</code>.
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowWhatsAppGuide(false)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl mt-2"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* CONFIGURE TELEGRAM MODAL */}
      {showTelegramConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm flex items-center gap-2">
                <Send className="w-4 h-4 text-cyan-400" />
                <span>Configure Telegram Bot</span>
              </h3>
              <button onClick={() => setShowTelegramConfigModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {telegramConfigError && (
              <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{telegramConfigError}</span>
              </div>
            )}

            <form onSubmit={handleConfigureTelegram} className="space-y-3.5">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Telegram Bot Token <span className="text-rose-400">*</span>
                </label>
                <input
                  type="password"
                  required
                  placeholder="e.g. 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
                  value={telegramBotTokenInput}
                  onChange={(e) => setTelegramBotTokenInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-xs"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Obtained from @BotFather when creating your Telegram Bot.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Recipient Chat ID <span className="text-slate-500 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. 987654321"
                  value={telegramChatIdInput}
                  onChange={(e) => setTelegramChatIdInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-xs"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Your Telegram numeric ID from @userinfobot or your channel ID.
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-850 text-[10px] text-slate-400 leading-relaxed font-sans">
                The server will verify credentials via <code>api.telegram.org/getMe</code>. In local development, verified credentials are saved to local .env atomically.
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowTelegramConfigModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={configuringTelegram}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl flex items-center gap-1.5 disabled:opacity-50"
                >
                  {configuringTelegram && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{configuringTelegram ? 'Verifying...' : 'Verify & Connect'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONFIGURE WHATSAPP MODAL */}
      {showWhatsAppConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" />
                <span>Configure WhatsApp Business</span>
              </h3>
              <button onClick={() => setShowWhatsAppConfigModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {whatsappConfigError && (
              <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{whatsappConfigError}</span>
              </div>
            )}

            <form onSubmit={handleConfigureWhatsApp} className="space-y-3.5">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Meta Phone Number ID <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 104829104820194"
                  value={whatsappPhoneIdInput}
                  onChange={(e) => setWhatsappPhoneIdInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Found in Meta Developer Dashboard → WhatsApp → API Setup.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Meta System User Access Token <span className="text-rose-400">*</span>
                </label>
                <input
                  type="password"
                  required
                  placeholder="EAAG..."
                  value={whatsappTokenInput}
                  onChange={(e) => setWhatsappTokenInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Permanent System User Token with <code>whatsapp_business_messaging</code> permission.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Recipient Phone (E.164) <span className="text-slate-500 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. +14155552671"
                  value={whatsappRecipientInput}
                  onChange={(e) => setWhatsappRecipientInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  International format starting with + and country code.
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-855 text-[10px] text-slate-400 leading-relaxed font-sans">
                The server validates the Phone Number ID against Meta Graph API (<code>GET /v18.0/&#123;id&#125;</code>) without sending messages. On Render, set environment variables in your Render Dashboard.
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowWhatsAppConfigModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={configuringWhatsApp}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl flex items-center gap-1.5 disabled:opacity-50"
                >
                  {configuringWhatsApp && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{configuringWhatsApp ? 'Verifying with Meta...' : 'Verify & Connect'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default NotificationCenterView;
