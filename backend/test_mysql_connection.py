import pymysql
import traceback

try:
    print("正在尝试连接MySQL...")
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='123456',
        connect_timeout=5
    )
    print('连接成功!')
    
    # 测试查询
    with conn.cursor() as cursor:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        print(f"找到 {len(databases)} 个数据库:")
        for db in databases:
            print(f"  - {db[0]}")
    
    conn.close()
    print("连接已关闭")
    
except Exception as e:
    print(f'连接失败: {e}')
    print(f'错误类型: {type(e).__name__}')
    traceback.print_exc()