# Quantitative Finance Basics

## Option Pricing Models

### Black-Scholes Model
The Black-Scholes model provides a partial differential equation (PDE) for the evolution of an option price under the risk-neutral measure.
Key assumptions include:
- The stock price follows a Geometric Brownian Motion (GBM).
- The risk-free rate $r$ and volatility $\sigma$ are constant.
- No transaction costs or taxes.

The formula for a call option is:
$$C(S, t) = N(d_1)S_t - N(d_2)Ke^{-r(T-t)}$$

### Heston Model
Unlike Black-Scholes, the Heston model relaxes the constant volatility assumption. It assumes volatility is a stochastic process following a square-root diffusion.

## Risk Management
Value at Risk (VaR) measures the potential loss in value of a risky asset or portfolio over a defined period for a given confidence interval.