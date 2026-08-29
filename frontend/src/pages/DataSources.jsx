import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Loader from '../components/Common/Loader';
import { Database, CheckCircle2, AlertCircle, RefreshCw, Settings, Info, CloudCheck } from 'lucide-react';

export default function DataSources({ onNavigate }) {
    const [sources, setSources] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    async function fetchStatuses() {
        try {
            setError(null);
            const res = await api.getDataSources();
            if (res && res.sources) {
                setSources(res.sources);
            } else {
                throw new Error('Invalid server response format.');
            }
        } catch (err) {
            setError(err.message || 'Failed to retrieve connection statuses.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }

    useEffect(() => {
        fetchStatuses();
    }, []);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchStatuses();
    };

    if (loading) {
        return <Loader text="Probing clinical databases and verifying metadata connections..." />;
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
            {/* Page Header */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="space-y-1">
                    <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                        <Database className="w-8 h-8 text-medical-500 shrink-0" />
                        <span>Clinical Data Connections</span>
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 font-semibold">
                        Manage, audit, and configure connection endpoints for underlying medical research training sets.
                    </p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 bg-white font-bold text-xs rounded-xl shadow-sm transition-all duration-200 disabled:opacity-50"
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                    {refreshing ? 'Refreshing...' : 'Scan Connections'}
                </button>
            </div>

            {/* Info Warning */}
            <div className="bg-amber-50/60 border border-amber-200/60 p-4.5 rounded-2xl flex items-start gap-3">
                <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                    <h4 className="font-extrabold text-amber-900">RAG Grounding & Compliance Audits</h4>
                    <p className="text-amber-800 leading-relaxed font-semibold">
                        To ensure complete medical factuality and dialogue realism, the patient simulator hooks directly into academic data adapters. Ensure your local paths are configured correctly in the backend environment variables to enable production clinical grounding.
                    </p>
                </div>
            </div>

            {error ? (
                <div className="text-center p-12 bg-red-50 border border-red-100 rounded-2xl space-y-3">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
                    <h3 className="font-bold text-red-800 text-sm">Connection Audit Failed</h3>
                    <p className="text-xs text-red-650 max-w-md mx-auto">{error}</p>
                    <button
                        onClick={fetchStatuses}
                        className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold"
                    >
                        Retry Connection Scan
                    </button>
                </div>
            ) : (
                <div className="grid sm:grid-cols-2 gap-6">
                    {sources.map((src) => {
                        const statusMap = {
                            'Configured': {
                                pill: 'bg-emerald-50 text-emerald-800 border-emerald-200',
                                dot: 'bg-emerald-500'
                            },
                            'Available': {
                                pill: 'bg-blue-50 text-blue-800 border-blue-200',
                                dot: 'bg-blue-500'
                            },
                            'Not connected': {
                                pill: 'bg-slate-100 text-slate-700 border-slate-200',
                                dot: 'bg-slate-450'
                            }
                        };
                        const theme = statusMap[src.status] || statusMap['Not connected'];

                        return (
                            <div
                                key={src.id}
                                className="bg-white border border-slate-205 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col justify-between space-y-5"
                            >
                                <div className="space-y-2.5">
                                    <div className="flex justify-between items-start gap-4">
                                        <span className="px-2 py-0.5 bg-slate-100 text-slate-500 border border-slate-200 rounded font-bold text-[9px] uppercase tracking-wider">
                                            {src.category}
                                        </span>
                                        <div className={`px-2.5 py-0.5 border rounded-full text-[10px] font-bold inline-flex items-center gap-1.5 ${theme.pill}`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${theme.dot}`} />
                                            {src.status}
                                        </div>
                                    </div>
                                    <h3 className="text-base font-extrabold text-slate-950">{src.name}</h3>
                                    <p className="text-xs font-semibold text-slate-650 leading-relaxed">{src.description}</p>
                                </div>

                                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] font-bold text-slate-400">
                                    <span className="font-mono">ID: {src.id}</span>
                                    <span className="text-medical-600 hover:underline cursor-pointer flex items-center gap-1">
                                        <Settings className="w-3 h-3" /> Details
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
