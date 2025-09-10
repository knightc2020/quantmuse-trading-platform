#pragma once
#include "common/types.hpp"
#include <memory>
#include <map>
#include <mutex>

namespace trading {

class RiskManager {
public:
    struct RiskLimits {
        double max_position_size;
        double max_drawdown;
        double max_leverage;
        double daily_loss_limit;
        double position_concentration;
    };

    RiskManager(const RiskLimits& limits);
    bool checkOrderRisk(const Order& order, const Portfolio& portfolio);
    void updateRiskMetrics(const Portfolio& portfolio);
    std::map<std::string, double> getRiskMetrics() const;

private:
    RiskLimits limits_;
    std::map<std::string, double> current_metrics_;
    std::mutex mutex_;
};

} // namespace trading 