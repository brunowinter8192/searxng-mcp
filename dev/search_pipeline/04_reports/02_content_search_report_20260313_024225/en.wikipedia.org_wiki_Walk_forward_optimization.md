# Walk forward optimization - Wikipedia
**URL:** https://en.wikipedia.org/wiki/Walk_forward_optimization
**Domain:** en.wikipedia.org
**Score:** 128.0
**Source:** scraped
**Query:** walk-forward validation time series cross-validation trading

---

[Jump to content](https://en.wikipedia.org/wiki/Walk_forward_optimization#bodyContent)
From Wikipedia, the free encyclopedia
Method used in finance to determine the optimal parameters for a trading strategy
**Walk forward optimization** is a method used in [finance](https://en.wikipedia.org/wiki/Finance "Finance") to determine the optimal parameters for a [trading strategy](https://en.wikipedia.org/wiki/Trading_strategy "Trading strategy") and to determine the robustness of the strategy. Walk Forward Analysis was presented by Robert E. Pardo in his book _"Design, Testing and Optimization of Trading Systems"_ in 1992 and expanded in the second edition in 2008. Walk Forward Analysis is now widely considered the "gold standard" in trading strategy validation. The trading strategy is optimized with in-sample data for a time window in a data series. The remaining data is reserved for [out of sample testing](https://en.wikipedia.org/wiki/Out_of_sample_testing "Out of sample testing"). A small portion of the reserved data following the in-sample data is tested and the results are recorded. The in-sample time window is shifted forward by the period covered by the out of sample test, and the process repeated. Lastly, all of the recorded results are used to assess the trading strategy. 
After the most suitable parameters are found, the system is run using another segment of data. The two segments of data do not overlap each other. This is what it means to do one walk-forward or out-of-sample test. It is the culmination of the following methods and aids in creation of robust systems. 
Past data is used for __of a trading system. It refers to applying a trading system to historical data to verify how a system would have performed during the specified time period and is useful if a system was not profitable in the past.
_**Forward testing**_ (also known as _**Walk forward testing**_) is the simulation of the real markets' data on paper only. One moves along the markets live and is not using real money, but virtually trading in the markets to understand their movements better. Hence, it is also called _**Paper Trading**_. Forward performance testing is a simulation of actual trading and involves following the system's logic in a live market. 
## Overview
One of the biggest issues with system development is that many systems do not hold up into the future. There are several reasons for this. The first is that the system is not based on a valid premise. Another is that the testing is not sound for reasons such as: 
  * Lack of robustness in a system due to improper parameters. A system is considered robust if it runs well in any market conditions.
  * Inconsistent rules and improper testing of the system using 'out-of-sample' and 'in-sample' data.


_**Walk Forward Analysis**_ does optimization on a training set; test on a period after the set and then rolls it all forward and repeats the process. We have multiple out-of-sample periods and look at these results combined. Walk forward analysis was first presented by Robert E. Pardo in the first version of his book _Design, Testing and Optimization of Trading Systems_ in 1992.. The first accurate software implementation of Walk Forward Analysis was in Pardo Corporation's pioneering application _Advanced Trade_ r and then in increasingly advanced versions in other applications such as _Blast_ and _XT_. Walking forward can keep a trading model a step ahead. Walk forward is so called, as we have multiple walk training and testing periods is less likely to suffer from [over-fitting](https://en.wikipedia.org/wiki/Overfitting "Overfitting"). This article was originally published in Futures (defunct) presented Walk Forward Analysis in nascent form. 
_Walk forward testing allows us to develop a trading system while maintaining a reasonable 'degree of freedom'_. Walk-forward testing carries the idea of 'out-of-sample' testing to the next level. It is a specific application of a technique known as [Cross

[Content truncated...]