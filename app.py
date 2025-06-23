from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import math
from datetime import datetime
import pandas as pd
from utils import load_scores
from yahooquery import Ticker
import subprocess
import sys
from scoring.composite_scorer import CompositeScorer
from scoring.config_manager import ScoringConfigManager as ConfigManager
from collectors.volume_analysis import VolumeAnalyzer

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins for API routes

def load_processed_data():
    """Load and merge score data with historical data."""
    try:
        # Try to load scores first
        scores_data = load_scores()
        
        # Load stock data as fallback/supplement
        data_file = os.path.join("cache", "stock_data.json")
        with open(data_file, 'r') as f:
            stock_data = json.load(f)

        records = []
        
        # Process scored stocks first (with complete scoring data)
        if scores_data and scores_data.get('scores'):
            for ticker, data in scores_data.get('scores', {}).items():
                record = {
                    'ticker': ticker,
                    'price': data['price'],
                    'score': data['score'],
                    'score_details': data['score_details'],
                    'timestamp': data['timestamp'],
                    'has_enhanced_scoring': True
                }
                
                # Add historical data if available
                if ticker in stock_data:
                    record['history'] = stock_data[ticker].get('historical_data')
                    # Add fundamental data
                    for key in ['market_cap', 'pe', 'forward_pe', 'dividend_yield', 'beta', 'year_high', 'year_low']:
                        if key in stock_data[ticker]:
                            record[key] = stock_data[ticker][key]
                
                records.append(record)
        
        # Add unscored stocks with basic data structure for testing
        if stock_data:
            scored_tickers = set(scores_data.get('scores', {}).keys()) if scores_data else set()
            
            for ticker, data in stock_data.items():
                if ticker not in scored_tickers:
                    # Create basic scoring structure for unscored stocks
                    record = {
                        'ticker': ticker,
                        'price': data.get('current_price', 0),
                        'score': 0,  # Default score for unscored stocks
                        'score_details': {
                            'legacy_score': 0,
                            'legacy_details': {},
                            'layered_score': 0,
                            'layered_details': {
                                'layer_scores': {
                                    'quality_gate': 0,
                                    'dip_signal': 0,
                                    'reversal_spark': 0,
                                    'risk_adjustment': 0
                                },
                                'layer_details': {
                                    'quality_gate': {},
                                    'dip_signal': {},
                                    'reversal_spark': {},
                                    'risk_modifiers': {}
                                }
                            }
                        },
                        'timestamp': '2025-06-22T00:00:00',
                        'has_enhanced_scoring': False,
                        'history': data.get('historical_data')
                    }
                    
                    # Add fundamental data
                    for key in ['market_cap', 'pe', 'forward_pe', 'dividend_yield', 'beta', 'year_high', 'year_low']:
                        if key in data:
                            record[key] = data[key]
                    
                    records.append(record)
        
        if not records:
            return None
            
        df = pd.DataFrame(records)
        # Sort by score descending, then by has_enhanced_scoring
        df = df.sort_values(['has_enhanced_scoring', 'score'], ascending=[False, False])
        return df
        
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading processed data: {e}")
        return None

@app.route('/api/stats')
def get_stats():
    """API endpoint for summary statistics."""
    try:
        df = load_processed_data()
        if df is None or len(df) == 0:
            return jsonify({'error': 'No data available'}), 404
        
        # Clean and validate data before processing
        avg_score = df['score'].mean()
        avg_score = 0.0 if pd.isna(avg_score) else float(avg_score)
        
        top_score = df.iloc[0]['score']
        top_score = 0.0 if pd.isna(top_score) else float(top_score)
        
        # Handle timestamp parsing safely
        try:
            last_update = pd.to_datetime(df['timestamp']).max().strftime('%Y-%m-%d %H:%M')
        except:
            last_update = datetime.now().strftime('%Y-%m-%d %H:%M')
            
        stats = {
            'total_stocks': len(df),
            'avg_score': avg_score,
            'top_scorer': str(df.iloc[0]['ticker']),
            'top_score': top_score,
            'last_update': last_update
        }
        
        # Clean the stats to ensure JSON serialization
        cleaned_stats = clean_data_for_json(stats)
        return jsonify(cleaned_stats)
        
    except Exception as e:
        print(f"❌ Error in get_stats: {e}")
        # Return a fallback response instead of crashing
        return jsonify({
            'total_stocks': 0,
            'avg_score': 0.0,
            'top_scorer': 'N/A',
            'top_score': 0.0,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'error': 'Stats temporarily unavailable'
        }), 200

@app.route('/api/stocks')
def get_stocks():
    """API endpoint for all stock data."""
    df = load_processed_data()
    if df is None:
        return jsonify({'error': 'No data available'}), 404
    
    # Clean the data to ensure JSON serialization
    cleaned_data = clean_data_for_json(df.to_dict('records'))
    return jsonify(cleaned_data)

@app.route('/api/stock/<ticker>')
def get_stock_detail(ticker):
    """API endpoint for individual stock data with enhanced 4-layer scoring."""
    df = load_processed_data()
    if df is None:
        return jsonify({'error': 'No data available'}), 404
    
    stock_data = df[df['ticker'] == ticker.upper()]
    if stock_data.empty:
        return jsonify({'error': f'Stock {ticker} not found'}), 404
    
    stock_record = stock_data.to_dict('records')[0]
    
    # Convert history data to expected format if it exists
    if stock_record.get('history') and isinstance(stock_record['history'], dict):
        history_dict = stock_record['history']
        if 'close' in history_dict and 'dates' in history_dict:
            # Convert to array of objects format
            dates = history_dict['dates']
            prices = history_dict['close']
            stock_record['history'] = [
                {'date': date, 'price': price} 
                for date, price in zip(dates, prices)
            ]
        else:
            # If data format is unexpected, set to empty array
            stock_record['history'] = []
    
    # Extract current volume from historical data if available
    if 'historical_data' in stock_record and isinstance(stock_record['historical_data'], dict):
        hist_data = stock_record['historical_data']
        if 'volume' in hist_data and hist_data['volume']:
            # Add current volume (last day) to the response
            stock_record['volume'] = hist_data['volume'][-1]
            stock_record['prev_close'] = hist_data['close'][-2] if len(hist_data['close']) > 1 else hist_data['close'][-1]
            
            # Add enhanced volume analysis using VolumeAnalyzer
            try:
                volume_analyzer = VolumeAnalyzer()
                # Create DataFrame for volume analysis
                volume_df = pd.DataFrame({
                    'Close': hist_data['close'],
                    'Volume': hist_data['volume'], 
                    'High': hist_data['high'],
                    'Low': hist_data['low']
                }, index=pd.to_datetime(hist_data['dates']))
                
                # Get comprehensive volume analysis
                volume_analysis = volume_analyzer.analyze_volume_patterns(volume_df, ticker.upper())
                stock_record['volume_analysis'] = volume_analysis
                print(f"✅ Enhanced volume analysis added for {ticker}")
                
            except Exception as vol_error:
                print(f"⚠️ Error calculating volume analysis for {ticker}: {vol_error}")
                stock_record['volume_analysis'] = {}
        else:
            stock_record['volume'] = stock_record.get('avg_volume', 0)
            stock_record['prev_close'] = stock_record.get('current_price', 0)
            stock_record['volume_analysis'] = {}
    else:
        # Fallback to avg_volume if no historical data
        stock_record['volume'] = stock_record.get('avg_volume', 0)
        stock_record['prev_close'] = stock_record.get('current_price', 0)
        stock_record['volume_analysis'] = {}
    
    # Try to get enhanced scoring data from the new 4-layer system
    try:
        # Load enhanced scoring data
        with open('cache/stock_data.json', 'r') as f:
            enhanced_data = json.load(f)
        
        if ticker.upper() in enhanced_data:
            ticker_data = enhanced_data[ticker.upper()]
            
            # Initialize composite scorer for enhanced analysis
            composite_scorer = CompositeScorer()
            
            # Get enhanced scoring breakdown  
            try:
                # Build DataFrame from ticker_data
                if 'historical_data' in ticker_data:
                    hist_data = ticker_data['historical_data']
                    df = pd.DataFrame({
                        'Close': hist_data['close'],
                        'Volume': hist_data['volume'], 
                        'High': hist_data['high'],
                        'Low': hist_data['low']
                    }, index=pd.to_datetime(hist_data['dates']))
                    
                    enhanced_score, enhanced_score_result = composite_scorer.calculate_composite_score(df, ticker.upper())
                
                    # Add enhanced scoring data to the response
                    if enhanced_score_result:
                        stock_record.update({
                            'layer_scores': enhanced_score_result.get('layer_scores', {}),
                            'layer_details': enhanced_score_result.get('layer_details', {}),
                            'investment_recommendation': enhanced_score_result.get('investment_recommendation', {}),
                            'methodology_compliance': enhanced_score_result.get('methodology_compliance', {}),
                            'overall_grade': enhanced_score_result.get('overall_grade', 'F'),
                            'enhanced_score': enhanced_score
                        })
                        print(f"✅ Enhanced scoring data added for {ticker}")
                    else:
                        print(f"⚠️ No enhanced scoring result for {ticker}")
                else:
                    print(f"⚠️ No historical data for {ticker}")
                    
            except Exception as scoring_error:
                print(f"❌ Error calculating enhanced score for {ticker}: {scoring_error}")
                # Add default enhanced scoring structure
                stock_record.update({
                    'layer_scores': {'quality_gate': 0, 'dip_signal': 0, 'reversal_spark': 0, 'risk_adjustment': 0},
                    'layer_details': {},
                    'investment_recommendation': {'action': 'AVOID', 'confidence': 'high', 'reason': 'Scoring error'},
                    'methodology_compliance': {'passes_quality_gate': False, 'in_dip_sweet_spot': False, 'has_reversal_signals': False},
                    'overall_grade': 'F',
                    'enhanced_score': 0
                })
        else:
            print(f"⚠️ No enhanced data found for {ticker}")
                
    except Exception as e:
        print(f"❌ Error loading enhanced data for {ticker}: {e}")
    
    # Clean the data to prevent NaN JSON serialization errors
    cleaned_record = clean_data_for_json(stock_record)
    
    return jsonify(cleaned_record)

def _to_native_py_type(val):
    """Converts numpy types to native Python types for JSON serialization."""
    if val is None:
        return None
    
    # Handle pandas/numpy NaN values
    if pd.isna(val):
        return None
        
    # Handle Python float NaN
    if isinstance(val, float) and (val != val):  # NaN check
        return None
        
    # Handle infinity values
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if val == float('inf') or val == float('-inf'):
            return None
    
    # Handle datetime types
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
        
    # Handle numpy types
    if hasattr(val, 'item'):
        try:
            result = val.item()
            # Double-check for NaN after conversion
            if isinstance(result, float) and (result != result):
                return None
            return result
        except (ValueError, OverflowError):
            return None
    
    return val

def clean_data_for_json(data):
    """Recursively clean data structure to ensure JSON serialization."""
    if isinstance(data, dict):
        return {key: clean_data_for_json(value) for key, value in data.items()}
    elif isinstance(data, (list, tuple)):
        return [clean_data_for_json(item) for item in data]
    else:
        return _to_native_py_type(data)

@app.route('/api/stock_details/<ticker>')
def get_stock_extra_details(ticker):
    """API endpoint for fetching extra details for a stock from local cached data."""
    try:
        print(f"Fetching details for ticker: {ticker}")
        
        # First try to get data from local stock_data.json cache
        details = {}
        
        # Load from stock_data.json (contains market_cap, pe, etc.)
        try:
            with open('cache/stock_data.json', 'r') as f:
                stock_data = json.load(f)
            
            if ticker.upper() in stock_data:
                cached_data = stock_data[ticker.upper()]
                
                # Extract market details from cached data
                details['market_cap'] = _to_native_py_type(cached_data.get('market_cap'))
                details['forward_pe'] = _to_native_py_type(cached_data.get('forward_pe'))
                details['dividend_yield'] = _to_native_py_type(cached_data.get('dividend_yield'))
                details['52_week_high'] = _to_native_py_type(cached_data.get('year_high'))
                details['52_week_low'] = _to_native_py_type(cached_data.get('year_low'))
                
                print(f"✅ Found cached data for {ticker}: {details}")
                return jsonify(details)
            else:
                print(f"⚠️ No cached data found for {ticker} in stock_data.json")
                
        except FileNotFoundError:
            print(f"⚠️ stock_data.json not found")
        except Exception as cache_error:
            print(f"⚠️ Error reading cached data: {cache_error}")
        
        # Try to get data from master_list.json as fallback
        try:
            with open('cache/master_list.json', 'r') as f:
                master_data = json.load(f)
            
            if 'stocks' in master_data:
                for stock in master_data['stocks']:
                    if stock.get('ticker', '').upper() == ticker.upper():
                        details['market_cap'] = _to_native_py_type(stock.get('market_cap'))
                        details['52_week_high'] = _to_native_py_type(stock.get('52w_high'))
                        details['52_week_low'] = _to_native_py_type(stock.get('52w_low'))
                        # Note: master_list.json may not have forward_pe and dividend_yield
                        details['forward_pe'] = None
                        details['dividend_yield'] = None
                        
                        print(f"✅ Found fallback data for {ticker} from master_list: {details}")
                        return jsonify(details)
                        
        except FileNotFoundError:
            print(f"⚠️ master_list.json not found")
        except Exception as master_error:
            print(f"⚠️ Error reading master list data: {master_error}")
        
        # If no local data found, return empty response with appropriate message
        print(f"❌ No local data available for {ticker}")
        return jsonify({
            'market_cap': None,
            'forward_pe': None,
            'dividend_yield': None,
            '52_week_high': None,
            '52_week_low': None,
            '_note': 'Data served from local cache'
        })
        
    except Exception as e:
        print(f"❌ Error fetching extra details for {ticker} from local cache: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unable to fetch details for {ticker}'}), 500

@app.route('/api/tasks/run_fetch', methods=['POST'])
def run_fetch_task():
    """Endpoint to trigger the --fetch CLI command."""
    try:
        # Using sys.executable to ensure we use the same python interpreter
        subprocess.Popen([sys.executable, 'cli.py', '--fetch'])
        return jsonify({'message': 'Fetch task started successfully. This may take a few minutes.'}), 202
    except Exception as e:
        return jsonify({'error': f'Failed to start fetch task: {e}'}), 500

@app.route('/api/tasks/run_score', methods=['POST'])
def run_score_task():
    """Endpoint to trigger the --score CLI command."""
    try:
        subprocess.Popen([sys.executable, 'cli.py', '--score'])
        return jsonify({'message': 'Score task started successfully. This may take several minutes.'}), 202
    except Exception as e:
        return jsonify({'error': f'Failed to start score task: {e}'}), 500

@app.route('/api/scoring/save-parameters', methods=['POST'])
def save_scoring_parameters():
    """Save scoring parameters to configuration file."""
    try:
        parameters = request.json
        if not parameters:
            return jsonify({'error': 'No parameters provided'}), 400
        
        # Create config directory if it doesn't exist
        os.makedirs('config', exist_ok=True)
        
        # Save parameters to JSON file
        with open('config/scoring_parameters.json', 'w') as f:
            json.dump({
                'parameters': parameters,
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }, f, indent=2)
        
        print(f"✅ Scoring parameters saved successfully")
        return jsonify({'message': 'Scoring parameters saved successfully'}), 200
        
    except Exception as e:
        print(f"❌ Error saving scoring parameters: {e}")
        return jsonify({'error': f'Failed to save parameters: {e}'}), 500

@app.route('/api/scoring/load-parameters', methods=['GET'])
def load_scoring_parameters():
    """Load scoring parameters from configuration file."""
    try:
        if os.path.exists('config/scoring_parameters.json'):
            with open('config/scoring_parameters.json', 'r') as f:
                config = json.load(f)
            return jsonify(config.get('parameters', {})), 200
        else:
            # Return default parameters
            default_params = {
                'quality_gate_weight': 35,
                'dip_signal_weight': 45,
                'reversal_spark_weight': 15,
                'risk_adjustment_weight': 10,
                'quality_fcf_threshold': 0,
                'quality_pe_multiplier': 1.2,
                'quality_debt_ebitda_max': 3.0,
                'quality_roe_min': 0.10,
                'quality_margin_min': 0.05,
                'dip_sweet_spot_min': 15,
                'dip_sweet_spot_max': 40,
                'dip_rsi_oversold_min': 25,
                'dip_rsi_oversold_max': 35,
                'dip_volume_spike_min': 1.5,
                'dip_volume_spike_max': 3.0,
                'reversal_rsi_min': 30,
                'reversal_volume_threshold': 1.2,
                'reversal_price_action_weight': 0.5,
                'strong_buy_threshold': 80,
                'buy_threshold': 70,
                'watch_threshold': 50,
                'avoid_threshold': 40
            }
            return jsonify(default_params), 200
            
    except Exception as e:
        print(f"❌ Error loading scoring parameters: {e}")
        return jsonify({'error': f'Failed to load parameters: {e}'}), 500

@app.route('/api/scoring/test-parameters', methods=['POST'])
def test_scoring_parameters():
    """Test new scoring parameters against current stock data."""
    try:
        test_data = request.json
        parameters = test_data.get('parameters', {})
        sample_size = test_data.get('sample_size', 50)
        
        # Load current stock data
        df = load_processed_data()
        if df is None:
            return jsonify({'error': 'No stock data available'}), 404
        
        print(f"📊 Total stocks available: {len(df)}")
        print(f"📊 Stocks with enhanced scoring: {len(df[df['has_enhanced_scoring'] == True])}")
        print(f"📊 Stocks without scoring: {len(df[df['has_enhanced_scoring'] == False])}")
        
        # Get random sample of stocks (not just first N)
        sample_size = min(sample_size, len(df))  # Don't exceed available data
        if sample_size <= len(df):
            sample_stocks = df.sample(n=sample_size, random_state=42).to_dict('records')
        else:
            sample_stocks = df.to_dict('records')
        
        print(f"📊 Testing with {len(sample_stocks)} randomly sampled stocks")
        
        results = []
        for stock in sample_stocks:
            # Simulate new scoring based on parameters and real data
            result = simulate_new_scoring_with_real_data(stock, parameters)
            results.append(result)
        
        # Enhanced summary statistics
        enhanced_stocks = [r for r in results if r.get('has_enhanced_data', False)]
        basic_stocks = [r for r in results if not r.get('has_enhanced_data', False)]
        
        response_data = {
            'results': results,
            'summary': {
                'total_tested': len(results),
                'enhanced_scoring_count': len(enhanced_stocks),
                'basic_data_count': len(basic_stocks),
                'avg_score_change': sum(r['score_change'] for r in results) / len(results) if results else 0,
                'recommendation_changes': sum(1 for r in results if r['recommendation_changed']),
                'data_issues': sum(1 for r in results if r['data_issues']),
                'unique_tickers': len(set(r['ticker'] for r in results)),
                'score_range': {
                    'min_new_score': min(r['new_score'] for r in results) if results else 0,
                    'max_new_score': max(r['new_score'] for r in results) if results else 0,
                    'avg_new_score': sum(r['new_score'] for r in results) / len(results) if results else 0
                }
            }
        }
        
        # Clean the data to ensure JSON serialization
        cleaned_response = clean_data_for_json(response_data)
        return jsonify(cleaned_response), 200
        
    except Exception as e:
        print(f"❌ Error testing scoring parameters: {e}")
        return jsonify({'error': f'Failed to test parameters: {e}'}), 500

def simulate_new_scoring(stock_record, parameters):
    """Simulate new scoring for a stock record with new parameters."""
    try:
        old_score = stock_record.get('score', 0)
        
        # Get current layer scores
        layer_scores = stock_record.get('score_details', {}).get('layer_scores', {})
        
        # Calculate new weighted scores
        new_quality_score = (layer_scores.get('quality_gate', 0) / 35) * parameters.get('quality_gate_weight', 35)
        new_dip_score = (layer_scores.get('dip_signal', 0) / 45) * parameters.get('dip_signal_weight', 45)
        new_reversal_score = (layer_scores.get('reversal_spark', 0) / 15) * parameters.get('reversal_spark_weight', 15)
        new_risk_adjustment = layer_scores.get('risk_adjustment', 0)
        
        new_score = new_quality_score + new_dip_score + new_reversal_score + new_risk_adjustment
        
        # Determine recommendations
        old_recommendation = get_recommendation_from_score(old_score, 'old')
        new_recommendation = get_recommendation_from_score(new_score, 'new', parameters)
        
        # Check for data issues
        data_issues = []
        layer_details = stock_record.get('score_details', {}).get('layer_details', {})
        
        if not layer_details.get('quality_gate'):
            data_issues.append('missing_quality_gate')
        if not layer_details.get('dip_signal'):
            data_issues.append('missing_dip_signal')
        if not layer_details.get('reversal_spark'):
            data_issues.append('missing_reversal_spark')
        
        return {
            'ticker': stock_record.get('ticker'),
            'old_score': old_score,
            'new_score': new_score,
            'score_change': new_score - old_score,
            'old_recommendation': old_recommendation,
            'new_recommendation': new_recommendation,
            'recommendation_changed': old_recommendation != new_recommendation,
            'layer_scores': {
                'quality_gate': new_quality_score,
                'dip_signal': new_dip_score,
                'reversal_spark': new_reversal_score,
                'risk_adjustment': new_risk_adjustment
            },
            'data_issues': len(data_issues) > 0,
            'issues': data_issues
        }
        
    except Exception as e:
        return {
            'ticker': stock_record.get('ticker', 'UNKNOWN'),
            'error': str(e),
            'old_score': 0,
            'new_score': 0,
            'score_change': 0,
            'old_recommendation': 'ERROR',
            'new_recommendation': 'ERROR',
            'recommendation_changed': False,
            'data_issues': True,
            'issues': ['calculation_error']
        }

def simulate_new_scoring_with_real_data(stock_record, parameters):
    """Simulate new scoring for a stock record using real fundamental data."""
    try:
        ticker = stock_record.get('ticker', 'UNKNOWN')
        old_score = stock_record.get('score', 0)
        has_enhanced_data = stock_record.get('has_enhanced_scoring', False)
        
        # Get current layer scores if available
        score_details = stock_record.get('score_details', {})
        layered_details = score_details.get('layered_details', {})
        layer_scores = layered_details.get('layer_scores', {})
        
        # Initialize new scores
        new_quality_score = 0
        new_dip_score = 0
        new_reversal_score = 0
        new_risk_adjustment = 0
        
        data_issues = []
        calculation_details = {}
        
        if has_enhanced_data and layer_scores:
            # Use existing layer scores and reweight them
            new_quality_score = (layer_scores.get('quality_gate', 0) / 35) * parameters.get('quality_gate_weight', 35)
            new_dip_score = (layer_scores.get('dip_signal', 0) / 45) * parameters.get('dip_signal_weight', 45)
            new_reversal_score = (layer_scores.get('reversal_spark', 0) / 15) * parameters.get('reversal_spark_weight', 15)
            new_risk_adjustment = layer_scores.get('risk_adjustment', 0)
            calculation_details['method'] = 'enhanced_reweight'
        else:
            # Calculate basic scores from fundamental data
            calculation_details['method'] = 'fundamental_calculation'
            
            # Quality Gate Score (based on fundamentals)
            pe_ratio = stock_record.get('pe')
            forward_pe = stock_record.get('forward_pe')
            market_cap = stock_record.get('market_cap')
            dividend_yield = stock_record.get('dividend_yield', 0)
            
            quality_points = 0
            
            # PE Ratio check
            if pe_ratio and not pd.isna(pe_ratio) and pe_ratio > 0:
                pe_max = parameters.get('quality_pe_multiplier', 50)
                if pe_ratio <= pe_max:
                    quality_points += 15  # Good P/E ratio
                    calculation_details['pe_check'] = f'✅ P/E {pe_ratio:.1f} <= {pe_max}'
                else:
                    calculation_details['pe_check'] = f'❌ P/E {pe_ratio:.1f} > {pe_max}'
            elif pe_ratio and not pd.isna(pe_ratio) and pe_ratio < 0:
                # Negative P/E (losses) - penalize but don't completely fail
                quality_points += 5
                calculation_details['pe_check'] = f'⚠️ Negative P/E {pe_ratio:.1f}'
            else:
                data_issues.append('missing_pe_ratio')
                calculation_details['pe_check'] = '❌ Missing P/E data'
            
            # Market cap check (prefer larger companies for quality)
            if market_cap and not pd.isna(market_cap) and market_cap > 0:
                if market_cap > 10_000_000_000:  # $10B+
                    quality_points += 10
                    calculation_details['market_cap_check'] = f'✅ Large cap ${market_cap/1e9:.1f}B'
                elif market_cap > 2_000_000_000:  # $2B+
                    quality_points += 5
                    calculation_details['market_cap_check'] = f'⚠️ Mid cap ${market_cap/1e9:.1f}B'
                else:
                    calculation_details['market_cap_check'] = f'❌ Small cap ${market_cap/1e9:.1f}B'
            else:
                data_issues.append('missing_market_cap')
                calculation_details['market_cap_check'] = '❌ Missing market cap'
            
            # Dividend yield bonus
            if dividend_yield and dividend_yield > 0 and not pd.isna(dividend_yield):
                bonus_points = min(dividend_yield * 2, 10)  # Up to 10 points for good dividend
                quality_points += bonus_points
                calculation_details['dividend_check'] = f'✅ Dividend yield {dividend_yield:.2f}%'
            else:
                calculation_details['dividend_check'] = '⚠️ No dividend'
            
            new_quality_score = (quality_points / 35) * parameters.get('quality_gate_weight', 35)
            
            # Dip Signal Score (basic calculation using price vs 52-week high)
            current_price = stock_record.get('price', 0)
            year_high = stock_record.get('year_high')
            year_low = stock_record.get('year_low')
            
            dip_points = 0
            
            if current_price and year_high and year_high > 0 and not pd.isna(current_price) and not pd.isna(year_high):
                drop_pct = ((year_high - current_price) / year_high) * 100
                sweet_spot_min = parameters.get('dip_sweet_spot_min', 15)
                sweet_spot_max = parameters.get('dip_sweet_spot_max', 40)
                
                if sweet_spot_min <= drop_pct <= sweet_spot_max:
                    dip_points += 30  # In sweet spot
                    calculation_details['dip_check'] = f'✅ In sweet spot: {drop_pct:.1f}% drop'
                elif drop_pct > sweet_spot_max:
                    dip_points += 15  # Deep value but risky
                    calculation_details['dip_check'] = f'⚠️ Deep drop: {drop_pct:.1f}% (over {sweet_spot_max}%)'
                elif drop_pct > 5:
                    dip_points += 10  # Minor dip
                    calculation_details['dip_check'] = f'⚠️ Small dip: {drop_pct:.1f}%'
                else:
                    calculation_details['dip_check'] = f'❌ No dip: {drop_pct:.1f}% drop'
            else:
                data_issues.append('missing_price_data')
                calculation_details['dip_check'] = '❌ Missing price/52w high data'
            
            # Volatility bonus (if near 52-week low, might be oversold)
            if (current_price and year_low and year_high and 
                not pd.isna(current_price) and not pd.isna(year_low) and not pd.isna(year_high) and
                year_high > year_low):
                position_in_range = (current_price - year_low) / (year_high - year_low)
                if position_in_range < 0.3:  # In bottom 30% of range
                    dip_points += 10
                    calculation_details['volatility_check'] = f'✅ Near 52w low: {position_in_range:.2f}'
                else:
                    calculation_details['volatility_check'] = f'⚠️ Position in range: {position_in_range:.2f}'
            
            new_dip_score = (dip_points / 45) * parameters.get('dip_signal_weight', 45)
            
            # Reversal Spark (basic momentum indicators)
            reversal_points = 0
            
            # Beta analysis (volatility can indicate momentum)
            beta = stock_record.get('beta')
            if beta and not pd.isna(beta):
                if 0.8 <= beta <= 1.5:  # Moderate beta suggests good momentum potential
                    reversal_points += 8
                    calculation_details['beta_check'] = f'✅ Good beta: {beta:.2f}'
                elif beta > 1.5:
                    reversal_points += 4  # High volatility
                    calculation_details['beta_check'] = f'⚠️ High beta: {beta:.2f}'
                else:
                    reversal_points += 2  # Low beta
                    calculation_details['beta_check'] = f'⚠️ Low beta: {beta:.2f}'
            else:
                data_issues.append('missing_beta')
                calculation_details['beta_check'] = '❌ Missing beta'
            
            # Price position (oversold bounce potential)
            if current_price and year_low and year_high:
                if position_in_range < 0.2:  # Very oversold
                    reversal_points += 7
                    calculation_details['oversold_check'] = f'✅ Very oversold: {position_in_range:.2f}'
                elif position_in_range < 0.4:  # Moderately oversold  
                    reversal_points += 4
                    calculation_details['oversold_check'] = f'⚠️ Oversold: {position_in_range:.2f}'
                else:
                    calculation_details['oversold_check'] = f'❌ Not oversold: {position_in_range:.2f}'
            
            new_reversal_score = (reversal_points / 15) * parameters.get('reversal_spark_weight', 15)
            
            # Risk adjustment (basic)
            risk_adjustment = 0
            if market_cap and market_cap > 5_000_000_000:  # Large cap safety
                risk_adjustment += 2
            if dividend_yield and dividend_yield > 1:  # Dividend safety
                risk_adjustment += 1
            
            new_risk_adjustment = risk_adjustment
        
        new_score = new_quality_score + new_dip_score + new_reversal_score + new_risk_adjustment
        
        # Determine recommendations
        old_recommendation = get_recommendation_from_score(old_score, 'old')
        new_recommendation = get_recommendation_from_score(new_score, 'new', parameters)
        
        # Clean all return values to ensure JSON serialization
        result = {
            'ticker': ticker,
            'old_score': _to_native_py_type(old_score),
            'new_score': _to_native_py_type(new_score),
            'score_change': _to_native_py_type(new_score - old_score),
            'old_recommendation': old_recommendation,
            'new_recommendation': new_recommendation,
            'recommendation_changed': old_recommendation != new_recommendation,
            'layer_scores': {
                'quality_gate': _to_native_py_type(new_quality_score),
                'dip_signal': _to_native_py_type(new_dip_score),
                'reversal_spark': _to_native_py_type(new_reversal_score),
                'risk_adjustment': _to_native_py_type(new_risk_adjustment)
            },
            'data_issues': len(data_issues) > 0,
            'issues': data_issues,
            'has_enhanced_data': has_enhanced_data,
            'calculation_details': calculation_details,
            'fundamental_data': {
                'pe_ratio': _to_native_py_type(stock_record.get('pe')),
                'market_cap': _to_native_py_type(stock_record.get('market_cap')),
                'dividend_yield': _to_native_py_type(stock_record.get('dividend_yield')),
                'beta': _to_native_py_type(stock_record.get('beta')),
                'year_high': _to_native_py_type(stock_record.get('year_high')),
                'year_low': _to_native_py_type(stock_record.get('year_low')),
                'current_price': _to_native_py_type(stock_record.get('price'))
            }
        }
        
        return clean_data_for_json(result)
        
    except Exception as e:
        return {
            'ticker': stock_record.get('ticker', 'UNKNOWN'),
            'error': str(e),
            'old_score': 0,
            'new_score': 0,
            'score_change': 0,
            'old_recommendation': 'ERROR',
            'new_recommendation': 'ERROR',
            'recommendation_changed': False,
            'data_issues': True,
            'issues': ['calculation_error'],
            'has_enhanced_data': False,
            'calculation_details': {'error': str(e)}
        }

def get_recommendation_from_score(score, type_='new', parameters=None):
    """Get recommendation from score using thresholds."""
    if type_ == 'new' and parameters:
        strong_buy_threshold = parameters.get('strong_buy_threshold', 80)
        buy_threshold = parameters.get('buy_threshold', 70)
        watch_threshold = parameters.get('watch_threshold', 50)
        avoid_threshold = parameters.get('avoid_threshold', 40)
    else:
        # Default thresholds
        strong_buy_threshold = 80
        buy_threshold = 70
        watch_threshold = 50
        avoid_threshold = 40
    
    if score >= strong_buy_threshold:
        return 'STRONG_BUY'
    elif score >= buy_threshold:
        return 'BUY'
    elif score >= watch_threshold:
        return 'WATCH'
    elif score >= avoid_threshold:
        return 'WEAK'
    else:
        return 'AVOID'

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Running on a different port (5001) to avoid conflicts with React dev server 