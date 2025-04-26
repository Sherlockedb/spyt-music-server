import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from base_downloader import BaseSpotifyDownloader

class MongoDBSpotifyDownloader(BaseSpotifyDownloader):
    """
    使用 MongoDB 存储统计信息和元数据的 Spotify 下载器
    """
    
    def __init__(self, client_id=None, client_secret=None, output_root="music_lib", 
                 output_format="{album}/[{artist}] {track-number}-{title}.{output-ext}", 
                 use_artist_dir=True, max_retries=3, retry_delay=5, log_file=None,
                 mongo_uri="mongodb://localhost:27017/", 
                 db_name="spotify_downloader", 
                 collection_prefix=""):
        """
        初始化 MongoDBSpotifyDownloader 类
        
        参数:
            client_id: Spotify API 客户端 ID
            client_secret: Spotify API 客户端密钥
            output_root: 输出根目录
            output_format: 输出文件格式（不含艺术家目录部分）
            use_artist_dir: 是否使用艺术家名称作为上层目录
            max_retries: 下载重试次数
            retry_delay: 重试间隔时间(秒)
            log_file: 日志文件路径
            mongo_uri: MongoDB 连接 URI
            db_name: 数据库名称
            collection_prefix: 集合名称前缀，用于区分不同的实例
        """
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            output_root=output_root,
            output_format=output_format,
            use_artist_dir=use_artist_dir,
            max_retries=max_retries,
            retry_delay=retry_delay,
            log_file=log_file
        )
        
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_prefix = collection_prefix
        
        # 初始化 MongoDB 连接
        self._init_mongodb()
    
    def _init_mongodb(self):
        """初始化 MongoDB 连接"""
        try:
            self.client = MongoClient(self.mongo_uri)
            # 测试连接
            self.client.admin.command('ping')
            logging.info(f"已连接到 MongoDB: {self.mongo_uri}")
            
            # 获取数据库
            self.db = self.client[self.db_name]
            logging.info(f"使用数据库: {self.db_name}")
            
        except ConnectionFailure as e:
            logging.error(f"MongoDB 连接失败: {e}")
            raise
        except Exception as e:
            logging.error(f"初始化 MongoDB 时出错: {e}")
            raise
    
    def _get_stats_collection(self, entity_type):
        """获取统计信息集合"""
        return self.db[f"{self.collection_prefix}{entity_type}_stats"]
    
    def _get_info_collection(self, entity_type):
        """获取元数据信息集合"""
        return self.db[f"{self.collection_prefix}{entity_type}_info"]
    
    def _save_stats(self, entity_type, entity_id, stats):
        """
        将统计信息保存到 MongoDB
        
        参数:
            entity_type: 实体类型 ('track', 'album', 'artist')
            entity_id: 实体ID
            stats: 统计信息
        
        返回:
            bool: 是否保存成功
        """
        try:
            collection = self._get_stats_collection(entity_type)
            
            # 将 entity_id 作为 _id 字段
            stats['_id'] = entity_id
            
            # 使用 upsert=True 来插入或更新
            result = collection.replace_one({'_id': entity_id}, stats, upsert=True)
            
            logging.info(f"统计信息已保存到 MongoDB: {entity_type}_{entity_id}")
            return True
        except PyMongoError as e:
            logging.error(f"保存统计信息到 MongoDB 失败: {e}")
            return False
    
    def _save_info(self, entity_type, entity_id, info):
        """
        将元数据信息保存到 MongoDB
        
        参数:
            entity_type: 实体类型 ('track', 'album', 'artist')
            entity_id: 实体ID
            info: 元数据信息
        
        返回:
            bool: 是否保存成功
        """
        try:
            collection = self._get_info_collection(entity_type)
            
            # 创建一个新的文档，包含 _id 和元数据
            document = {
                '_id': entity_id,
                'info': info
            }
            
            # 使用 upsert=True 来插入或更新
            result = collection.replace_one({'_id': entity_id}, document, upsert=True)
            
            logging.info(f"元数据信息已保存到 MongoDB: {entity_type}_{entity_id}")
            return True
        except PyMongoError as e:
            logging.error(f"保存元数据信息到 MongoDB 失败: {e}")
            return False
    
    def _load_stats(self, entity_type, entity_id):
        """
        从 MongoDB 加载统计信息
        
        参数:
            entity_type: 实体类型 ('track', 'album', 'artist')
            entity_id: 实体ID
        
        返回:
            dict|None: 统计信息，如果不存在则返回None
        """
        try:
            collection = self._get_stats_collection(entity_type)
            document = collection.find_one({'_id': entity_id})
            
            if document:
                logging.info(f"从 MongoDB 加载了统计信息: {entity_type}_{entity_id}")
                # 删除 _id 字段，使结果与基类期望的格式一致
                if '_id' in document:
                    del document['_id']
                return document
            else:
                logging.info(f"MongoDB 中没有找到统计信息: {entity_type}_{entity_id}")
                return None
                
        except PyMongoError as e:
            logging.warning(f"从 MongoDB 加载统计信息失败: {e}")
            return None
    
    def _load_info(self, entity_type, entity_id):
        """
        从 MongoDB 加载元数据信息
        
        参数:
            entity_type: 实体类型 ('track', 'album', 'artist')
            entity_id: 实体ID
        
        返回:
            dict|None: 元数据信息，如果不存在则返回None
        """
        try:
            collection = self._get_info_collection(entity_type)
            document = collection.find_one({'_id': entity_id})
            
            if document and 'info' in document:
                logging.info(f"从 MongoDB 加载了元数据信息: {entity_type}_{entity_id}")
                return document['info']
            else:
                logging.info(f"MongoDB 中没有找到元数据信息: {entity_type}_{entity_id}")
                return None
                
        except PyMongoError as e:
            logging.warning(f"从 MongoDB 加载元数据信息失败: {e}")
            return None
    
    def close(self):
        """关闭 MongoDB 连接"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
                logging.info("已关闭 MongoDB 连接")
        except Exception as e:
            logging.error(f"关闭 MongoDB 连接时出错: {e}")