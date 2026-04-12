import { useState, useEffect, useRef } from 'react';
import { chatAPI } from './services/api';
import './App.css';

function App() {
  const [sessionId, setSessionId]     = useState(null);
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState('');
  const [loading, setLoading]         = useState(false);
  const [needsReport, setNeedsReport] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const [step, setStep]               = useState(0);   // ← nouveau
  const [total, setTotal]             = useState(10);  // ← nouveau
  const [completed, setCompleted]     = useState(false); // ← nouveau
  const [reportUrl, setReportUrl]     = useState(null);  // ← nouveau
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ── Déclenchement automatique du rapport ──────────────────────
  // Quand needs_report passe à true, on génère le PDF immédiatement
  // sans attendre que l'utilisateur clique.
  useEffect(() => {
    if (needsReport && sessionId && !reportUrl) {
      handleGenerateReport();
    }
  }, [needsReport]);

  // ── Démarrage session ────────────────────────────────────────────
  const startNewSession = async () => {
    try {
      setLoading(true);
      setShowWelcome(false);
      const data = await chatAPI.startSession();
      setSessionId(data.session_id);
      setMessages([{ role: 'assistant', content: data.response }]);
      setNeedsReport(false);
      setCompleted(false);
      setStep(0);
      setTotal(10);
      setReportUrl(null);
    } catch (error) {
      console.error('Erreur démarrage session:', error);
      setMessages([{
        role: 'assistant',
        content: 'Erreur de connexion. Vérifiez que le backend est démarré.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  // ── Envoi message ────────────────────────────────────────────────
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || completed) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const data = await chatAPI.sendMessage(sessionId, userMessage);
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);

      // Mise à jour progression
      if (data.step  !== undefined) setStep(data.step);
      if (data.total !== undefined) setTotal(data.total);
      if (data.completed)           setCompleted(true);
      if (data.needs_report)        setNeedsReport(true);

    } catch (error) {
      console.error('Erreur envoi message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Erreur de connexion. Veuillez réessayer.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  // ── Génération rapport PDF ───────────────────────────────────────
  const handleGenerateReport = async () => {
    try {
      setLoading(true);
      const data = await chatAPI.generateReport(sessionId);
      const fullUrl = `http://localhost:8000${data.download_url}`;
      setReportUrl(fullUrl);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '✅ Votre rapport médical a été généré. Cliquez sur le bouton ci-dessous pour le télécharger.',
      }]);
    } catch (error) {
      console.error('Erreur génération rapport:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Une erreur est survenue lors de la génération du rapport. Veuillez réessayer.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  // ── Reset ────────────────────────────────────────────────────────
  const resetSession = () => {
    setSessionId(null);
    setMessages([]);
    setNeedsReport(false);
    setShowWelcome(true);
    setStep(0);
    setTotal(10);
    setCompleted(false);
    setReportUrl(null);
  };

  // ── Calcul pourcentage barre de progression ──────────────────────
  const progressPercent = total > 0 ? Math.round((step / total) * 100) : 0;

  // ════════════════════════════════════════════════════════════════
  // ÉCRAN D'ACCUEIL
  // ════════════════════════════════════════════════════════════════
  if (showWelcome) {
    return (
      <div className="app">
        <header className="header">
          <h1>🦟 Malidata - Assistant paludisme</h1>
          <p>Évaluation préliminaire des symptômes</p>
        </header>

        <div className="welcome-screen">
          <div className="welcome-content">
            <h2>Bienvenue sur Malidata</h2>
            <p>Assistant virtuel de pré-consultation pour la malaria</p>

            <div className="welcome-info">
              <div className="info-card">
                <h3>📋 Questionnaire Guidé</h3>
                <p>10 étapes médicales structurées</p>
              </div>
              <div className="info-card">
                <h3>🔒 Confidentiel & Sécurisé</h3>
                <p>Vos données sont protégées</p>
              </div>
              <div className="info-card">
                <h3>📄 Rapport PDF</h3>
                <p>Document pour votre médecin</p>
              </div>
            </div>

            <button className="start-button" onClick={startNewSession} disabled={loading}>
              {loading ? 'Démarrage...' : 'Démarrer l\'Évaluation'}
            </button>

            <p className="disclaimer">
              ⚠️ Cet outil ne remplace pas une consultation médicale professionnelle
            </p>
          </div>
        </div>

        <footer className="footer">
          <small>Malidata v2.0 - Pré-consultation médicale</small>
        </footer>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════
  // INTERFACE CHAT
  // ════════════════════════════════════════════════════════════════
  return (
    <div className="app">
      <header className="header">
        <h1>🦟 Malidata - Assistant paludisme</h1>
        <p>Évaluation préliminaire des symptômes</p>
        <button className="reset-btn" onClick={resetSession}>
          Nouvelle Session
        </button>
      </header>

      {/* ── Barre de progression ── */}
      {!completed && (
        <div className="progress-container">
          <div className="progress-labels">
            <span>Étape {step} / {total}</span>
            <span>{progressPercent}%</span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Barre de complétion ── */}
      {completed && (
        <div className="progress-container completed">
          <div className="progress-labels">
            <span>✅ Questionnaire terminé</span>
            <span>100%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: '100%' }} />
          </div>
        </div>
      )}

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">{msg.content}</div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-content typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Bouton téléchargement PDF ── */}
        {reportUrl && (
          <div className="report-banner">
            <p>✅ Rapport médical prêt</p>
            <div className="report-actions">
              <a href={reportUrl} target="_blank" rel="noopener noreferrer">
                <button className="download-btn">
                  📄 Télécharger le Rapport PDF
                </button>
              </a>
              <button className="reset-btn-secondary" onClick={resetSession}>
                Nouvelle Consultation
              </button>
            </div>
          </div>
        )}

        {/* ── Zone de saisie ── */}
        <form onSubmit={sendMessage} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={completed ? 'Consultation terminée' : 'Tapez votre réponse...'}
            disabled={loading || completed}
          />
          <button type="submit" disabled={loading || !input.trim() || completed}>
            Envoyer
          </button>
        </form>
      </div>

      <footer className="footer">
        <small>⚠️ Cet outil ne remplace pas une consultation médicale</small>
      </footer>
    </div>
  );
}

export default App;
