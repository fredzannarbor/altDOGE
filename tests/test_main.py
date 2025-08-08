"""Tests for the main script module."""

import pytest
import tempfile
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO
import sys

from cfr_agency_counter.main import (
    setup_argument_parser,
    validate_arguments,
    setup_logging,
    load_agencies,
    create_api_client,
    main
)
from cfr_agency_counter.models import Agency


class TestArgumentParser:
    """Test cases for argument parsing."""
    
    def test_setup_argument_parser(self):
        """Test argument parser setup."""
        parser = setup_argument_parser()
        
        assert isinstance(parser, argparse.ArgumentParser)
        assert 'agencies_file' in parser._option_string_actions or any(
            action.dest == 'agencies_file' for action in parser._actions
        )
    
    def test_parse_minimal_arguments(self):
        """Test parsing minimal required arguments."""
        parser = setup_argument_parser()
        
        args = parser.parse_args(['test_agencies.csv'])
        
        assert args.agencies_file == 'test_agencies.csv'
        assert args.output_dir == './results'
        assert args.format == ['csv', 'json']
        assert args.rate_limit == 1.0
        assert args.verbose is False
        assert args.quiet is False
    
    def test_parse_all_arguments(self):
        """Test parsing all available arguments."""
        parser = setup_argument_parser()
        
        args = parser.parse_args([
            'agencies.csv',
            '--output-dir', '/tmp/reports',
            '--format', 'csv', 'json',
            '--rate-limit', '0.5',
            '--timeout', '60',
            '--max-retries', '5',
            '--active-only',
            '--progress-interval', '5.0',
            '--verbose',
            '--limit', '10',
            '--dry-run'
        ])
        
        assert args.agencies_file == 'agencies.csv'
        assert args.output_dir == '/tmp/reports'
        assert args.format == ['csv', 'json']
        assert args.rate_limit == 0.5
        assert args.timeout == 60
        assert args.max_retries == 5
        assert args.active_only is True
        assert args.progress_interval == 5.0
        assert args.verbose is True
        assert args.limit == 10
        assert args.dry_run is True


class TestArgumentValidation:
    """Test cases for argument validation."""
    
    def create_test_args(self, **overrides):
        """Create test arguments with defaults."""
        defaults = {
            'agencies_file': 'test.csv',
            'output_dir': './results',
            'rate_limit': 1.0,
            'timeout': 30,
            'max_retries': 3,
            'progress_interval': 10.0,
            'limit': None,
            'verbose': False,
            'quiet': False
        }
        defaults.update(overrides)
        return argparse.Namespace(**defaults)
    
    def test_validate_arguments_success(self):
        """Test successful argument validation."""
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp_file:
            args = self.create_test_args(agencies_file=temp_file.name)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                args.output_dir = temp_dir
                errors = validate_arguments(args)
                
                assert errors == []
    
    def test_validate_missing_file(self):
        """Test validation with missing agencies file."""
        args = self.create_test_args(agencies_file='nonexistent.csv')
        
        errors = validate_arguments(args)
        
        assert len(errors) > 0
        assert any('not found' in error for error in errors)
    
    def test_validate_invalid_rate_limit(self):
        """Test validation with invalid rate limit."""
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp_file:
            args = self.create_test_args(
                agencies_file=temp_file.name,
                rate_limit=-1.0
            )
            
            errors = validate_arguments(args)
            
            assert any('Rate limit must be positive' in error for error in errors)
    
    def test_validate_invalid_timeout(self):
        """Test validation with invalid timeout."""
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp_file:
            args = self.create_test_args(
                agencies_file=temp_file.name,
                timeout=0
            )
            
            errors = validate_arguments(args)
            
            assert any('Timeout must be positive' in error for error in errors)
    
    def test_validate_conflicting_options(self):
        """Test validation with conflicting verbose/quiet options."""
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp_file:
            args = self.create_test_args(
                agencies_file=temp_file.name,
                verbose=True,
                quiet=True
            )
            
            errors = validate_arguments(args)
            
            assert any('Cannot specify both --verbose and --quiet' in error for error in errors)
    
    def test_validate_invalid_progress_interval(self):
        """Test validation with invalid progress interval."""
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp_file:
            args = self.create_test_args(
                agencies_file=temp_file.name,
                progress_interval=150.0
            )
            
            errors = validate_arguments(args)
            
            assert any('Progress interval must be between 0 and 100' in error for error in errors)


class TestLoggingSetup:
    """Test cases for logging setup."""
    
    def test_setup_logging_verbose(self):
        """Test logging setup with verbose mode."""
        args = argparse.Namespace(
            verbose=True,
            quiet=False,
            log_file=None
        )
        
        with patch('logging.basicConfig') as mock_config:
            setup_logging(args)
            
            mock_config.assert_called_once()
            call_args = mock_config.call_args
            assert call_args[1]['level'] == 10  # DEBUG level
    
    def test_setup_logging_quiet(self):
        """Test logging setup with quiet mode."""
        args = argparse.Namespace(
            verbose=False,
            quiet=True,
            log_file=None
        )
        
        with patch('logging.basicConfig') as mock_config:
            setup_logging(args)
            
            mock_config.assert_called_once()
            call_args = mock_config.call_args
            assert call_args[1]['level'] == 30  # WARNING level
    
    def test_setup_logging_custom_file(self):
        """Test logging setup with custom log file."""
        args = argparse.Namespace(
            verbose=False,
            quiet=False,
            log_file='custom.log'
        )
        
        with patch('logging.basicConfig') as mock_config, \
             patch('logging.FileHandler') as mock_file_handler:
            
            setup_logging(args)
            
            mock_file_handler.assert_called_with('custom.log')


class TestAgencyLoading:
    """Test cases for agency loading."""
    
    def create_test_csv_content(self):
        """Create test CSV content."""
        return """active,cfr_citation,parent_agency_name,agency_name,description
1,12 CFR 100-199,Treasury,Test Agency 1,Active CFR agency
0,13 CFR 200-299,Commerce,Test Agency 2,Inactive CFR agency
1,,Treasury,Test Agency 3,Active non-CFR agency"""
    
    def test_load_agencies_success(self):
        """Test successful agency loading."""
        csv_content = self.create_test_csv_content()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(csv_content)
            temp_file.flush()
            
            args = argparse.Namespace(
                agencies_file=temp_file.name,
                cfr_only=True,
                active_only=False,
                include_inactive=False,
                limit=None
            )
            
            try:
                agencies = load_agencies(args)
                
                # Should have 2 CFR agencies (active and inactive)
                assert len(agencies) == 2
                assert all(agency.cfr_citation for agency in agencies)
                
            finally:
                Path(temp_file.name).unlink()
    
    def test_load_agencies_active_only(self):
        """Test loading active agencies only."""
        csv_content = self.create_test_csv_content()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(csv_content)
            temp_file.flush()
            
            args = argparse.Namespace(
                agencies_file=temp_file.name,
                cfr_only=True,
                active_only=True,
                include_inactive=False,
                limit=None
            )
            
            try:
                agencies = load_agencies(args)
                
                # Should have 1 active CFR agency
                assert len(agencies) == 1
                assert agencies[0].active is True
                assert agencies[0].cfr_citation
                
            finally:
                Path(temp_file.name).unlink()
    
    def test_load_agencies_with_limit(self):
        """Test loading agencies with limit."""
        csv_content = self.create_test_csv_content()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(csv_content)
            temp_file.flush()
            
            args = argparse.Namespace(
                agencies_file=temp_file.name,
                cfr_only=True,
                active_only=False,
                include_inactive=False,
                limit=1
            )
            
            try:
                agencies = load_agencies(args)
                
                # Should be limited to 1 agency
                assert len(agencies) == 1
                
            finally:
                Path(temp_file.name).unlink()
    
    def test_load_agencies_file_error(self):
        """Test agency loading with file error."""
        args = argparse.Namespace(
            agencies_file='nonexistent.csv',
            cfr_only=True,
            active_only=False,
            include_inactive=False,
            limit=None
        )
        
        with pytest.raises(SystemExit):
            load_agencies(args)


class TestAPIClientCreation:
    """Test cases for API client creation."""
    
    def test_create_api_client_success(self):
        """Test successful API client creation."""
        args = argparse.Namespace(
            api_url='https://test.example.com/api',
            rate_limit=2.0,
            timeout=60,
            max_retries=5
        )
        
        with patch('cfr_agency_counter.main.FederalRegisterClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            client = create_api_client(args)
            
            mock_client_class.assert_called_once_with(
                base_url='https://test.example.com/api',
                rate_limit=2.0
            )
            assert client == mock_client
    
    def test_create_api_client_error(self):
        """Test API client creation with error."""
        args = argparse.Namespace(
            api_url='invalid-url',
            rate_limit=1.0,
            timeout=30,
            max_retries=3
        )
        
        with patch('cfr_agency_counter.main.FederalRegisterClient', side_effect=Exception("Invalid URL")):
            with pytest.raises(SystemExit):
                create_api_client(args)


class TestMainFunction:
    """Test cases for the main function."""
    
    def test_main_help(self):
        """Test main function with help argument."""
        with patch('sys.argv', ['cfr_agency_counter', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Help should exit with code 0
            assert exc_info.value.code == 0
    
    def test_main_validate_config(self):
        """Test main function with config validation."""
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp_file:
            with patch('sys.argv', ['cfr_agency_counter', temp_file.name, '--validate-config']), \
                 patch('cfr_agency_counter.main.Config.validate'), \
                 patch('builtins.print') as mock_print:
                
                result = main()
                
                assert result == 0
                mock_print.assert_called_with("Configuration is valid")
    
    def test_main_missing_file(self):
        """Test main function with missing agencies file."""
        with patch('sys.argv', ['cfr_agency_counter', 'nonexistent.csv']), \
             patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            
            result = main()
            
            assert result == 1
            assert "Configuration errors:" in mock_stderr.getvalue()
    
    def test_main_keyboard_interrupt(self):
        """Test main function with keyboard interrupt."""
        with patch('sys.argv', ['cfr_agency_counter', 'test.csv']), \
             patch('cfr_agency_counter.main.load_agencies', side_effect=KeyboardInterrupt), \
             patch('cfr_agency_counter.main.validate_arguments', return_value=[]), \
             patch('cfr_agency_counter.main.setup_logging'), \
             patch('builtins.print') as mock_print:
            
            result = main()
            
            assert result == 130
            mock_print.assert_called_with("\nProcess interrupted by user")
    
    @patch('cfr_agency_counter.main.generate_reports')
    @patch('cfr_agency_counter.main.process_agencies')
    @patch('cfr_agency_counter.main.create_api_client')
    @patch('cfr_agency_counter.main.load_agencies')
    @patch('cfr_agency_counter.main.setup_logging')
    @patch('cfr_agency_counter.main.validate_arguments')
    def test_main_success_flow(self, mock_validate, mock_setup_logging, mock_load_agencies,
                              mock_create_client, mock_process, mock_generate):
        """Test successful main function execution flow."""
        # Setup mocks
        mock_validate.return_value = []
        mock_agencies = [MagicMock()]
        mock_load_agencies.return_value = mock_agencies
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_results = MagicMock()
        mock_process.return_value = mock_results
        
        with patch('sys.argv', ['cfr_agency_counter', 'test.csv']):
            result = main()
        
        assert result == 0
        mock_validate.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_load_agencies.assert_called_once()
        mock_create_client.assert_called_once()
        # Check that functions were called (arguments will be complex Namespace objects)
        mock_process.assert_called_once()
        mock_generate.assert_called_once()
        mock_client.close.assert_called_once()