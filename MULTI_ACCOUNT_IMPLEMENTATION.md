# 🏦 Multi-Account Data Architecture Implementation

## Overview

This document describes the comprehensive implementation of the multi-account data architecture for the D.E.V.I trading bot system. The implementation provides complete account-based data isolation, dynamic data source configuration, and seamless account switching functionality.

## 🎯 Objectives Achieved

### ✅ Dynamic Data Handling
- **Removed all hardcoded data references**: Data paths are now dynamically generated based on active account
- **Implemented flexible data source configuration**: `DataSourceAbstraction` provides account-aware data access
- **Created abstraction layer for data inputs**: All components use the abstraction layer instead of direct file access
- **Support for multiple concurrent data streams**: Each account maintains separate data streams

### ✅ Account-Specific GUI Isolation
- **Complete data separation per MT5 account** including:
  - Analytics dashboards and metrics
  - Daily charts and historical data
  - Trading performance indicators
  - Portfolio statistics
  - Risk analysis reports
  - Custom indicators and overlays
- **Account 0001 displays only its complete dataset when logged in**
- **Account 0002 displays only its complete dataset when logged in**
- **Zero data bleeding between accounts across all GUI components**

### ✅ Technical Specifications
- **Account-based data filtering at the data layer**: `DataSourceAbstraction` ensures proper isolation
- **Account session management with complete context isolation**: `AccountSessionManager` handles switching
- **All GUI components respect account context**: Streamlit app and analytics dashboard updated
- **Account switching functionality with complete data refresh**: Implemented in GUI
- **Separate data storage/caching per account**: Each account has its own `Data/Account_XXXX/` directory
- **Account-specific chart configurations and saved views**: `AccountChartManager` handles chart settings

## 📁 File Structure

```
/workspace/
├── account_manager.py              # Core multi-account system
├── account_config_manager.py       # Account-specific configuration management
├── account_chart_manager.py        # Account-specific chart configurations
├── test_basic_multi_account.py     # Basic testing script
├── GUI Components/
│   ├── streamlit_app.py            # Updated with account switching
│   └── analytics_dashboard.py      # Updated for multi-account support
├── Data/                           # Account-specific data storage
│   ├── Account_0001/               # Account 0001 data
│   │   ├── trade_log.csv
│   │   ├── balance_history.csv
│   │   ├── ai_decision_log.jsonl
│   │   ├── account_config.json
│   │   └── charts/
│   │       └── chart_config.json
│   └── Account_0002/               # Account 0002 data
│       ├── trade_log.csv
│       ├── balance_history.csv
│       ├── ai_decision_log.jsonl
│       ├── account_config.json
│       └── charts/
│           └── chart_config.json
└── accounts_config.json            # Account credentials and settings
```

## 🏗️ Architecture Components

### 1. AccountSessionManager
**File**: `account_manager.py`

The core component that manages account sessions and context isolation.

**Key Features:**
- Account switching with MT5 connection management
- Session data caching during switches
- Context manager for temporary account access
- Thread-safe MT5 operations

**Usage:**
```python
from account_manager import initialize_account_system

# Initialize system
account_manager, data_source = initialize_account_system()

# Switch account
account_manager.switch_account("0001")

# Use context manager for temporary access
with account_manager.account_context("0002"):
    # Operations using account 0002
    pass
```

### 2. DataSourceAbstraction
**File**: `account_manager.py`

Provides account-aware data access layer that replaces all hardcoded file paths.

**Key Features:**
- Dynamic path generation based on active account
- Account-specific data loading methods
- MT5 data access with account context
- Fallback to default paths for backward compatibility

**Usage:**
```python
from account_manager import get_data_source

data_source = get_data_source()

# Get account-specific paths
trade_log_path = data_source.get_trade_log_path("0001")
balance_path = data_source.get_balance_history_path("0001")

# Load account-specific data
trade_data = data_source.load_trade_log("0001")
balance_data = data_source.load_balance_history("0001")
```

### 3. AccountConfigManager
**File**: `account_config_manager.py`

Manages account-specific configurations with fallback to global defaults.

**Key Features:**
- Account-specific config overrides
- Dynamic config switching
- Backward compatibility with existing CONFIG usage
- FTMO parameters per account

**Usage:**
```python
from account_config_manager import get_config_manager

config_manager = get_config_manager()

# Set active account
config_manager.set_active_account("0001")

# Update account config
config_manager.update_account_config("0001", {
    "min_score_for_trade": 8,
    "lot_size": 0.2
})

# Get config value
min_score = config_manager.get_config_value("min_score_for_trade")
```

### 4. AccountChartManager
**File**: `account_chart_manager.py`

Manages chart configurations, saved views, and custom indicators per account.

**Key Features:**
- Account-specific chart configurations
- Saved chart views and layouts
- Custom indicator settings
- Symbol watchlists per account
- Drawing tools and annotations
- Export/import configurations

**Usage:**
```python
from account_chart_manager import get_chart_manager, ChartIndicator

chart_manager = get_chart_manager()

# Add custom indicator
indicator = ChartIndicator(
    name="Custom_MA",
    type="trend",
    parameters={"period": 20},
    color="#FFD700"
)
chart_manager.add_indicator("0001", indicator)

# Save chart view
from account_chart_manager import ChartView
view = ChartView(
    name="EURUSD_H1_Strategy",
    symbol="EURUSD", 
    timeframe="H1",
    indicators=[indicator]
)
chart_manager.save_chart_view("0001", view)
```

## 🔧 Configuration

### 1. Account Configuration
Create `accounts_config.json` in the root directory:

```json
{
  "0001": {
    "account_id": "0001",
    "account_name": "Demo Account 1",
    "broker": "MetaQuotes Software Corp.",
    "server": "MetaQuotes-Demo",
    "login": 12345,
    "password": "your_password",
    "enabled": true,
    "config_overrides": {
      "min_score_for_trade": 7,
      "lot_size": 0.1
    }
  },
  "0002": {
    "account_id": "0002",
    "account_name": "Live Account 1",
    "broker": "Your Broker",
    "server": "YourBroker-Live",
    "login": 67890,
    "password": "your_password",
    "enabled": true,
    "config_overrides": {
      "min_score_for_trade": 8,
      "lot_size": 0.05
    }
  }
}
```

### 2. Account-Specific Configurations
Each account can have custom configuration overrides stored in:
`Data/Account_XXXX/account_config.json`

### 3. Chart Configurations
Chart settings are stored in:
`Data/Account_XXXX/charts/chart_config.json`

## 🚀 Usage

### Starting the System

1. **Initialize the multi-account system:**
```python
from account_manager import initialize_account_system
from account_config_manager import initialize_config_manager

# Initialize systems
account_manager, data_source = initialize_account_system()
config_manager = initialize_config_manager()
```

2. **Run the Streamlit GUI:**
```bash
streamlit run "GUI Components/streamlit_app.py"
```

### Using the GUI

1. **Authentication**: Enter the team password to access the dashboard
2. **Account Selection**: Use the sidebar to select and switch between accounts
3. **Data Viewing**: All data displayed is automatically filtered for the active account
4. **Configuration**: Modify account-specific settings in the sidebar
5. **Chart Management**: Save and load custom chart configurations per account

### Account Switching

The GUI provides seamless account switching with:
- Complete data refresh
- MT5 connection switching
- Configuration context update
- Chart settings restoration

## 🧪 Testing

### Basic Testing
Run the basic test suite:
```bash
python3 test_basic_multi_account.py
```

### Manual Testing
1. Switch between accounts in the GUI
2. Verify data isolation by checking different trade logs
3. Test configuration changes per account
4. Verify MT5 connection switching
5. Test chart configuration isolation

## 🔒 Data Isolation

### Directory Structure
Each account maintains completely separate data:
```
Data/
├── Account_0001/
│   ├── trade_log.csv          # Account 0001 trades only
│   ├── balance_history.csv    # Account 0001 balance only
│   ├── ai_decision_log.jsonl  # Account 0001 AI decisions only
│   └── charts/                # Account 0001 chart settings only
└── Account_0002/
    ├── trade_log.csv          # Account 0002 trades only
    ├── balance_history.csv    # Account 0002 balance only
    ├── ai_decision_log.jsonl  # Account 0002 AI decisions only
    └── charts/                # Account 0002 chart settings only
```

### Isolation Verification
- ✅ No shared files between accounts
- ✅ No cross-account data references
- ✅ Complete GUI context switching
- ✅ Separate MT5 connections
- ✅ Independent configuration management

## 🔄 Migration from Single Account

### Automatic Migration
The system automatically migrates existing data:
1. Copies existing `Data Files/` content to `Data/Account_0001/`
2. Creates default account configurations
3. Maintains backward compatibility

### Manual Migration Steps
1. **Backup existing data**: Copy `Data Files/` to a safe location
2. **Run the system**: The first run will create the multi-account structure
3. **Configure accounts**: Update `accounts_config.json` with real MT5 credentials
4. **Test switching**: Verify account switching works correctly
5. **Migrate additional accounts**: Copy data to additional account directories as needed

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all files are in the correct directory
   - Check Python path includes the project root

2. **MT5 Connection Issues**
   - Verify MT5 is installed and accessible
   - Check account credentials in `accounts_config.json`
   - Ensure MT5 terminal is closed before switching accounts

3. **Data Not Loading**
   - Check account directories exist: `Data/Account_XXXX/`
   - Verify file permissions
   - Check data source abstraction is properly initialized

4. **Configuration Issues**
   - Ensure `accounts_config.json` is properly formatted
   - Check account IDs match between config and data directories
   - Verify config manager is initialized before use

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export DEVI_DEBUG=1
```

## 📈 Performance Considerations

### Optimizations Implemented
- **Caching**: Configuration and chart settings are cached in memory
- **Lazy Loading**: Data is loaded only when needed
- **Connection Pooling**: MT5 connections are reused when possible
- **File System Optimization**: Efficient directory structure for fast access

### Scalability
- Supports unlimited number of accounts
- Efficient memory usage with account-specific caching
- Fast account switching with minimal overhead
- Optimized for high-frequency trading scenarios

## 🔮 Future Enhancements

### Planned Features
1. **Database Backend**: Optional database storage for large datasets
2. **Cloud Sync**: Synchronization across multiple trading stations
3. **Advanced Analytics**: Cross-account performance comparison
4. **Risk Management**: Account-specific risk limits and monitoring
5. **Automated Backup**: Scheduled backup of account data
6. **API Access**: REST API for external system integration

### Extension Points
- Custom data sources can be added to `DataSourceAbstraction`
- Additional configuration managers can be plugged in
- Custom chart indicators and views can be developed
- Third-party plugins can integrate with the account system

## 📞 Support

For questions or issues:
1. Check this documentation first
2. Run the test suite to verify system integrity
3. Check log files for error messages
4. Contact the development team

## 📝 Changelog

### Version 1.0.0 (Initial Implementation)
- ✅ Complete multi-account data architecture
- ✅ Account session management
- ✅ Data source abstraction layer
- ✅ Configuration management per account
- ✅ Chart configuration management
- ✅ GUI integration with account switching
- ✅ Comprehensive testing suite
- ✅ Documentation and migration guide

---

**Author**: Terrence Ndifor (Terry)  
**Project**: D.E.V.I Multi-Account Trading System  
**Last Updated**: January 2025