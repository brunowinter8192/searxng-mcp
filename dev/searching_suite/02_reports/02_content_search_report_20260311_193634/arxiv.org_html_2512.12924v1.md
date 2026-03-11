# Interpretable Hypothesis-Driven Trading: A Rigorous Walk-Forward ...
**URL:** https://arxiv.org/html/2512.12924v1
**Domain:** arxiv.org
**Score:** 16.0
**Source:** scraped
**Query:** walk-forward validation time series cross-validation trading

---

[License: CC BY 4.0](https://info.arxiv.org/help/license/index.html#licenses-available)
arXiv:2512.12924v1 [q-fin.TR] 15 Dec 2025
# Interpretable Hypothesis-Driven Trading: A Rigorous Walk-Forward Validation Framework for Market Microstructure Signals
Report issue for preceding element
Gagan Deep Department of Mathematics & Statistics, Texas Tech University. Email: gdeep@ttu.edu. Corresponding author. Akash Deep Department of Mathematics & Statistics, Texas Tech University. Email: akash.deep@ttu.edu. William Lamptey Department of Mathematics & Statistics, Texas Tech University. Email: wilampte@ttu.edu.
Report issue for preceding element
(December 15, 2025)
###### Abstract
Report issue for preceding element
We develop a rigorous walk-forward validation framework for algorithmic trading designed to mitigate overfitting and lookahead bias. Our methodology combines interpretable hypothesis-driven signal generation with reinforcement learning and strict out-of-sample testing. The framework enforces strict information set discipline, employs rolling window validation across 34 independent test periods, maintains complete interpretability through natural language hypothesis explanations, and incorporates realistic transaction costs and position constraints. Validating five market microstructure patterns across 100 US equities from 2015 to 2024, the system yields modest annualized returns (0.55%, Sharpe ratio 0.33) with exceptional downside protection (maximum drawdown −2.76%-2.76\%) and market-neutral characteristics (β=0.058\beta=0.058). Performance exhibits strong regime dependence, generating positive returns during high-volatility periods (0.60% quarterly, 2020–2024) while underperforming in stable markets (−0.16%-0.16\%, 2015–2019). We report statistically insignificant aggregate results (p-value 0.34) to demonstrate a reproducible, honest validation protocol that prioritizes interpretability and extends naturally to advanced hypothesis generators, including large language models. The key empirical finding reveals that daily OHLCV-based microstructure signals require elevated information arrival and trading activity to function effectively. The framework provides complete mathematical specifications and open-source implementation, establishing a template for rigorous trading system evaluation that addresses the reproducibility crisis in quantitative finance research. For researchers, practitioners, and regulators, this work demonstrates that interpretable algorithmic trading strategies can be rigorously validated without sacrificing transparency or regulatory compliance.
Report issue for preceding element
Keywords: Algorithmic Trading, Walk-Forward Validation, Market Microstructure, Interpretable Machine Learning, Reinforcement Learning, Backtesting Methodology
Report issue for preceding element
JEL Classification: G11, G12, C53, C63
Report issue for preceding element
##  1 Introduction
Report issue for preceding element
Quantitative trading research faces a reproducibility crisis. Studies consistently document trading strategies generating double-digit annual returns through backtesting, yet institutional investors report that over 90% of academic strategies fail when implemented with real capital (harvey2016backtesting). This credibility gap threatens the practical relevance of finance research and has generated increasing skepticism toward published trading anomalies. The fundamental problem is methodological: standard backtesting procedures suffer from overfitting through in-sample parameter optimization, lookahead bias through the use of information unavailable in real-time, and lack of interpretability through reliance on black-box machine learning models.
Report issue for preceding element
This paper develops a rigorous validation framework that addresses these deficiencies while maintaining generality across hypothesis generation approaches. Our framework makes four key methodological innovations. First, it enforces stri

[Content truncated...]