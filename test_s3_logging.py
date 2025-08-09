#!/usr/bin/env python3
"""
Test script for S3 to SQS notification and Lambda processing
Tests 4 different data types: JSON, Plain Text, NDJSON, and CSV
Verifies data in Elasticsearch datastream instead of SQS
"""

import argparse
import boto3
import json
import time
import uuid
import random
import logging
import csv
import io
import requests
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class S3LoggingTest:
    def __init__(self, region: str, s3_bucket: str, lambda_function: Optional[str] = None, 
                 elasticsearch_url: Optional[str] = None, elasticsearch_api_key: Optional[str] = None,
                 elasticsearch_datastream: Optional[str] = None):
        self.region = region
        self.s3_bucket = s3_bucket
        self.lambda_function = lambda_function
        self.elasticsearch_url = elasticsearch_url
        self.elasticsearch_api_key = elasticsearch_api_key
        self.elasticsearch_datastream = elasticsearch_datastream or "logs-aws.s3-default"
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=region)
        if lambda_function:
            self.lambda_client = boto3.client('lambda', region_name=region)

    def generate_json_log_content(self) -> str:
        """Generate realistic JSON log content"""
        timestamp = datetime.utcnow().isoformat()
        request_id = str(uuid.uuid4())
        
        log_entry = {
            "@timestamp": timestamp,  # Use @timestamp for better Elasticsearch compatibility
            "timestamp": timestamp,
            "level": random.choice(["INFO", "WARN", "ERROR", "DEBUG"]),
            "request_id": request_id,
            "message": random.choice([
                "User authentication successful",
                "API request processed",
                "Database query completed",
                "Cache operation performed"
            ]),
            "user_id": f"user_{random.randint(1000, 9999)}",
            "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "duration_ms": random.randint(10, 5000),
            "status_code": random.choice([200, 201, 400, 404, 500]),
            "test_marker": f"s3-test-{uuid.uuid4().hex[:8]}"  # Unique marker for test identification
        }
        
        return json.dumps(log_entry, indent=2)

    def generate_plain_text_log_content(self) -> str:
        """Generate plain text log content (Apache/Nginx style)"""
        timestamp = datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")
        ip_address = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
        method = random.choice(["GET", "POST", "PUT", "DELETE"])
        path = random.choice(["/api/users", "/api/orders", "/health", "/metrics", "/login"])
        status_code = random.choice([200, 201, 400, 404, 500])
        size = random.randint(100, 10000)
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "curl/7.68.0"
        ])
        test_marker = f"test-{uuid.uuid4().hex[:8]}"
        
        lines = []
        for _ in range(random.randint(5, 15)):
            log_line = f'{ip_address} - - [{timestamp}] "{method} {path} HTTP/1.1" {status_code} {size} "-" "{user_agent}" test_marker={test_marker}'
            lines.append(log_line)
            
        return "\n".join(lines)

    def generate_ndjson_log_content(self) -> str:
        """Generate NDJSON (newline-delimited JSON) log content"""
        lines = []
        base_time = datetime.utcnow()
        test_marker = f"ndjson-test-{uuid.uuid4().hex[:8]}"
        
        for i in range(random.randint(5, 20)):
            timestamp = (base_time + timedelta(seconds=i)).isoformat()
            log_entry = {
                "@timestamp": timestamp,
                "timestamp": timestamp,
                "level": random.choice(["INFO", "WARN", "ERROR"]),
                "service": random.choice(["api-gateway", "user-service", "order-service", "payment-service"]),
                "message": random.choice([
                    "Request processed successfully",
                    "Database connection established",
                    "Cache miss occurred",
                    "Rate limit exceeded",
                    "Authentication failed"
                ]),
                "request_id": str(uuid.uuid4()),
                "user_id": f"user_{random.randint(1000, 9999)}",
                "trace_id": f"trace_{uuid.uuid4().hex[:16]}",
                "span_id": f"span_{uuid.uuid4().hex[:8]}",
                "test_marker": test_marker
            }
            lines.append(json.dumps(log_entry))
            
        return "\n".join(lines)

    def generate_csv_log_content(self) -> str:
        """Generate CSV format log content"""
        output = io.StringIO()
        writer = csv.writer(output)
        test_marker = f"csv-test-{uuid.uuid4().hex[:8]}"
        
        # Write header
        writer.writerow([
            "timestamp", "level", "service", "message", "user_id", 
            "ip_address", "response_time_ms", "status_code", "bytes_sent", "test_marker"
        ])
        
        # Write data rows
        base_time = datetime.utcnow()
        for i in range(random.randint(10, 30)):
            timestamp = (base_time + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([
                timestamp,
                random.choice(["INFO", "WARN", "ERROR"]),
                random.choice(["web-server", "api-server", "db-server", "cache-server"]),
                random.choice([
                    "Request completed",
                    "Connection timeout",
                    "Query executed",
                    "Cache updated"
                ]),
                f"user_{random.randint(1000, 9999)}",
                f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
                random.randint(10, 3000),
                random.choice([200, 201, 400, 404, 500]),
                random.randint(100, 50000),
                test_marker
            ])
        
        return output.getvalue()

    def upload_test_file(self, file_key: str, content: str, content_type: str = 'text/plain') -> bool:
        """Upload a test file to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=file_key,
                Body=content,
                ContentType=content_type
            )
            logger.info(f"Successfully uploaded {file_key} to {self.s3_bucket} ({len(content)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {file_key}: {str(e)}")
            return False

    def generate_test_files(self) -> List[Dict]:
        """Generate test files for all 4 data types"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        test_id = uuid.uuid4().hex[:8]
        
        test_files = [
            {
                "type": "JSON",
                "key": f"json-logs/{timestamp}_{test_id}_application.json",
                "content": self.generate_json_log_content(),
                "content_type": "application/json"
            },
            {
                "type": "Plain Text",
                "key": f"plain-logs/{timestamp}_{test_id}_access.log",
                "content": self.generate_plain_text_log_content(),
                "content_type": "text/plain"
            },
            {
                "type": "NDJSON",
                "key": f"ndjson-logs/{timestamp}_{test_id}_microservices.ndjson",
                "content": self.generate_ndjson_log_content(),
                "content_type": "application/x-ndjson"
            },
            {
                "type": "CSV",
                "key": f"csv-logs/{timestamp}_{test_id}_metrics.csv",
                "content": self.generate_csv_log_content(),
                "content_type": "text/csv"
            }
        ]
        
        return test_files

    def check_elasticsearch_data(self, search_window_seconds: int = 120) -> bool:
        """Check if recent data exists in Elasticsearch datastream"""
        if not self.elasticsearch_url or not self.elasticsearch_api_key:
            logger.warning("Elasticsearch URL or API key not provided, skipping Elasticsearch check")
            return True
            
        try:
            # Calculate time range (last N seconds)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(seconds=search_window_seconds)
            
            # Elasticsearch search query
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": start_time.isoformat(),
                                        "lte": end_time.isoformat()
                                    }
                                }
                            }
                        ]
                    }
                },
                "sort": [
                    {"@timestamp": {"order": "desc"}}
                ],
                "size": 50,
                "_source": ["@timestamp", "message", "test_marker", "level", "service", "user_id"]
            }
            
            # Make request to Elasticsearch
            url = f"{self.elasticsearch_url.rstrip('/')}/{self.elasticsearch_datastream}/_search"
            headers = {
                "Authorization": f"ApiKey {self.elasticsearch_api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Searching Elasticsearch for recent data in {self.elasticsearch_datastream}")
            logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")
            
            response = requests.post(url, headers=headers, json=search_query, timeout=30)
            
            if response.status_code == 200:
                search_results = response.json()
                hits = search_results.get('hits', {}).get('hits', [])
                total_hits = search_results.get('hits', {}).get('total', {})
                
                if isinstance(total_hits, dict):
                    total_count = total_hits.get('value', 0)
                else:
                    total_count = total_hits
                
                logger.info(f"✅ Found {total_count} documents in the last {search_window_seconds} seconds")
                
                if hits:
                    logger.info("Recent log entries:")
                    for i, hit in enumerate(hits[:10]):  # Show first 10 entries
                        source = hit.get('_source', {})
                        timestamp = source.get('@timestamp', 'N/A')
                        message = source.get('message', 'N/A')
                        test_marker = source.get('test_marker', '')
                        level = source.get('level', '')
                        service = source.get('service', '')
                        
                        logger.info(f"  [{i+1}] {timestamp} - {level} - {message[:100]}{'...' if len(message) > 100 else ''}")
                        if test_marker:
                            logger.info(f"      Test marker: {test_marker}")
                    
                    return True
                else:
                    logger.warning("No recent documents found in Elasticsearch")
                    return False
                    
            elif response.status_code == 404:
                logger.error(f"Datastream '{self.elasticsearch_datastream}' not found")
                return False
            else:
                logger.error(f"Elasticsearch search failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Elasticsearch check: {str(e)}")
            return False

    def check_lambda_logs(self) -> bool:
        """Check if Lambda function has recent log entries"""
        if not self.lambda_function:
            logger.info("No Lambda function specified, skipping log check")
            return True
            
        try:
            # Get recent log events from CloudWatch
            logs_client = boto3.client('logs', region_name=self.region)
            log_group_name = f"/aws/lambda/{self.lambda_function}"
            
            # Get log streams from the last hour
            end_time = int(time.time() * 1000)
            start_time = end_time - (60 * 60 * 1000)  # 1 hour ago
            
            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_time,
                endTime=end_time,
                limit=50
            )
            
            recent_events = response.get('events', [])
            if recent_events:
                logger.info(f"Found {len(recent_events)} recent Lambda log events")
                # Log some recent events for debugging
                for event in recent_events[-3:]:  # Last 3 events
                    logger.info(f"Lambda log: {event['message'].strip()}")
                return True
            else:
                logger.warning("No recent Lambda log events found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check Lambda logs: {str(e)}")
            return False

    def list_s3_objects_by_prefix(self, prefix: str) -> List[str]:
        """List S3 objects with given prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            logger.error(f"Failed to list S3 objects with prefix {prefix}: {str(e)}")
            return []

    def run_test(self, wait_time: int = 120) -> bool:
        """Run the complete test with all 4 data types"""
        logger.info("Starting S3 logging test with 4 different data types")
        
        # Generate and upload test files
        test_files = self.generate_test_files()
        uploaded_files = []
        
        logger.info(f"Uploading {len(test_files)} test files...")
        for file_info in test_files:
            logger.info(f"Uploading {file_info['type']} file: {file_info['key']}")
            
            if self.upload_test_file(
                file_info['key'], 
                file_info['content'], 
                file_info['content_type']
            ):
                uploaded_files.append(file_info)
            else:
                logger.error(f"Failed to upload {file_info['type']} file")
                return False
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} test files")
        
        # Show content samples
        for file_info in uploaded_files:
            content_sample = file_info['content'][:200] + "..." if len(file_info['content']) > 200 else file_info['content']
            logger.info(f"{file_info['type']} sample content:\n{content_sample}")
        
        # Wait for processing
        logger.info(f"Waiting {wait_time} seconds for S3 → SQS → Lambda → Elasticsearch processing...")
        time.sleep(wait_time)
        
        # Check Elasticsearch for recent data
        elasticsearch_success = self.check_elasticsearch_data(search_window_seconds=120)
        
        # Check Lambda processing
        lambda_success = self.check_lambda_logs()
        
        # Verify file organization in S3
        self.verify_s3_organization(uploaded_files)
        
        # Cleanup test files
        self.cleanup_test_files([f['key'] for f in uploaded_files])
        
        # Overall test result
        overall_success = elasticsearch_success and lambda_success
        if overall_success:
            logger.info("✅ All tests passed!")
        else:
            logger.error("❌ Some tests failed!")
            
        return overall_success

    def verify_s3_organization(self, uploaded_files: List[Dict]):
        """Verify that files are properly organized in S3"""
        logger.info("Verifying S3 file organization...")
        
        prefixes = ["json-logs/", "plain-logs/", "ndjson-logs/", "csv-logs/"]
        
        for prefix in prefixes:
            objects = self.list_s3_objects_by_prefix(prefix)
            expected_files = [f for f in uploaded_files if f['key'].startswith(prefix)]
            
            if len(objects) >= len(expected_files):
                logger.info(f"✅ {prefix}: Found {len(objects)} files (expected at least {len(expected_files)})")
            else:
                logger.warning(f"⚠️ {prefix}: Found {len(objects)} files (expected at least {len(expected_files)})")

    def cleanup_test_files(self, file_keys: List[str]):
        """Clean up test files from S3"""
        logger.info("Cleaning up test files...")
        for file_key in file_keys:
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=file_key)
                logger.info(f"Deleted {file_key}")
            except Exception as e:
                logger.warning(f"Failed to delete {file_key}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Test S3 to SQS notification and Lambda processing with multiple data types')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket name')
    parser.add_argument('--lambda-function', help='Lambda function name (optional)')
    parser.add_argument('--elasticsearch-url', help='Elasticsearch URL')
    parser.add_argument('--elasticsearch-api-key', help='Elasticsearch API key')
    parser.add_argument('--elasticsearch-datastream', default='logs-aws.s3-default', help='Elasticsearch datastream name')
    parser.add_argument('--wait-time', type=int, default=120, help='Wait time in seconds')
    
    args = parser.parse_args()
    
    # Initialize and run test
    test = S3LoggingTest(
        region=args.region,
        s3_bucket=args.s3_bucket,
        lambda_function=args.lambda_function,
        elasticsearch_url=args.elasticsearch_url,
        elasticsearch_api_key=args.elasticsearch_api_key,
        elasticsearch_datastream=args.elasticsearch_datastream
    )
    
    success = test.run_test(wait_time=args.wait_time)
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()