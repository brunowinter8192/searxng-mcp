# Time Series Forecasting: A Practical Guide to Exploratory Data ...
**URL:** https://towardsdatascience.com/time-series-forecasting-a-practical-guide-to-exploratory-data-analysis-a101dc5f85b1/
**Domain:** towardsdatascience.com
**Score:** 0.4
**Source:** scraped
**Query:** feature engineering financial time series prediction

---

# Time Series Forecasting: A Practical Guide to Exploratory Data Analysis
How to use Exploratory Data Analysis to drive information from time series data and enhance feature engineering using Python 
May 9, 2024
17 min read
Photo by [Ales Krivec](https://unsplash.com/@aleskrivec?utm_source=medium&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=medium&utm_medium=referral)
## Introduction
Time series analysis certainly represents one of the most widespread topics in the field of data science and machine learning: whether predicting financial events, energy consumption, product sales or stock market trends, this field has always been of great interest to businesses.
Obviously, the great increase in data availability, combined with the constant progress in machine learning models, has made this topic even more interesting today. Alongside traditional forecasting methods derived from statistics (e.g. regressive models, ARIMA models, exponential smoothing), techniques relating to machine learning (e.g. tree-based models) and deep learning (e.g. LSTM Networks, CNNs, Transformer-based Models) have emerged for some time now.
Despite the huge differences between these techniques, there is a preliminary step that must be done, no matter what the model is: _Exploratory Data Analysis._
In statistics, **Exploratory Data Analysis** (EDA) is a discipline consisting in analyzing and visualizing data in order to summarize their main characteristics and gain relevant information from them. This is of considerable importance in the data science field because it allows to lay the foundations to another important step: _feature engineering_. That is, the practice that consists on creating, transforming and extracting features from the dataset so that the model can work to the best of its possibilities.
The objective of this article is therefore to define a clear exploratory data analysis template, focused on time series, which can summarize and highlight the most important characteristics of the dataset. To do this, we will use some common Python libraries such as _Pandas_ , _Seaborn_ and S _tatsmodel_.
## Data
Let’s first define the dataset: for the purposes of this article, we will take Kaggle’s **[Hourly Energy Consumption](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption)** data. This dataset relates to PJM Hourly Energy Consumption data, a regional transmission organization in the United States, that serves electricity to Delaware, Illinois, Indiana, Kentucky, Maryland, Michigan, New Jersey, North Carolina, Ohio, Pennsylvania, Tennessee, Virginia, West Virginia, and the District of Columbia.
The hourly power consumption data comes from PJM’s website and are in megawatts (MW).
## Exploratory Data Analysis
Let’s now define which are the most significant analyses to be performed when dealing with time series.
For sure, one of the most important thing is to plot the data: graphs can highlight many features, such as patterns, unusual observations, changes over time, and relationships between variables. As already said, the insight that emerge from these plots must then be taken into consideration, as much as possible, into the forecasting model. Moreover, some mathematical tools such as descriptive statistics and time series decomposition, will also be very useful.
Said that, the EDA I’m proposing in this article consists on six steps: Descriptive Statistics, Time Plot, Seasonal Plots, Box Plots, Time Series Decomposition, Lag Analysis.
### 1. Descriptive Statistics
Descriptive statistic is a summary statistic that quantitatively describes or summarizes features from a collection of structured data.
Some metrics that are commonly used to describe a dataset are: measures of central tendency (e.g. _mean_ , _median_), measures of dispersion (e.g. _range_ , _standard deviation_), and measure of position (e.g. _percentiles_ , _quartile_). All of them can be summarized by the so called **five number summary** , whic

[Content truncated...]