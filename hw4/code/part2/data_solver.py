import csv
import os

from graphframes import *
from pyspark import SQLContext
from pyspark import SparkConf, SparkContext


def getData(sc, filename):
    """
    Load data from raw text file into RDD and transform.
    Hint: transfromation you will use: map(<lambda function>).
    Args:
        sc (SparkContext): spark context.
        filename (string): hw2.txt cloud storage URI.
    Returns:
        RDD: RDD list of tuple of (<User>, [friend1, friend2, ... ]),
        each user and a list of user's friends
    """
    # read text file into RDD
    data = sc.textFile(filename)
    data = data.map(lambda line: line.split("\t")).map(
        lambda line: (int(line[0]), [int(x) for x in line[1].split(",")] if len(
            line[1]) else []))
    return data


def get_vertices(data, sqlcontext):
    """
    get vertices
    :param data: RDD list of tuple of (<User>, [friend1, friend2, ... ]),
        each user and a list of user's friends
    :param sqlcontext: SQLContext
    :return: dataframe
    """
    vertices = data.map(lambda line: (line[0],))

    return sqlcontext.createDataFrame(vertices, schema=["id"])


def get_edges(data, sqlcontext):
    """
    get edges
    :param data: RDD list of tuple of (<User>, [friend1, friend2, ... ]),
        each user and a list of user's friends
    :param sqlcontext: SQLContext
    :return:
    """

    def map_friends(line):
        """
        map function to construct edge between friends
        construct a pair of ((friend1, friend2) -> common friends list)
        if two friends are already direct friends, then common friends list
        is empty.
        :param line: tuple of (<User>, [friend1, friend2, ... ]),
                    each user and a list of user's friends
        :return: friend pair
        """
        user = line[0]
        friends = line[1]
        for i in range(len(friends)):
            yield (user, friends[i])

    edges = data.flatMap(map_friends)
    return sqlcontext.createDataFrame(edges, schema=["src", "dst"])


def save_nodes(nodes):
    """
    save node list to csv
    :param nodes: list that contain nodes in the cluster of 25 users
    :return:
    """
    with open("nodes.csv", "w") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["node"])
        csv_writer.writerows(nodes)


def connected_components(graph):
    """
    run connected components on graph
    :param graph: Graph contains vertices and edges
    :return:
    """
    print("connected components")
    result = graph.connectedComponents(algorithm="graphx")

    # How many clusters / connected components in total for this dataset
    cluster_num = result.select("component").distinct().count()
    print("clusters amount: ", cluster_num)
    print()

    # How many users in the top 10 clusters?
    print("number of users in top 10 cluster")
    res1 = result.groupBy("component").count().orderBy('count',
                                                       ascending=False)
    res2 = res1.head(10)
    total = 0
    for row in res2:
        total += row["count"]
        print("cluster id:\t%d\tnumber of users:\t%d" % (
            row["component"], row["count"]))
    print("Total number of users in top 10 cluster:\t", total)
    print()

    # What are the user ids for the cluster which has 25 users?
    print("user ids for the cluster which has 25 users")
    cluster_id = res1.where(res1["count"] == 25).select("component").collect()
    cluster_id = [row["component"] for row in cluster_id]
    user_list = result.where(result["component"].isin(cluster_id)).select(
        "id").collect()
    user_ls = [row["id"] for row in user_list]
    user_ls.sort()
    save_nodes([[node] for node in user_ls])
    print(user_ls)
    print()

    # get edges for 25 nodes
    df_edges = graph.edges.filter(
        graph.edges.dst.isin(user_ls) & graph.edges.src.isin(user_ls))
    df_edges = df_edges.rdd.map(
        lambda x: (user_ls.index(x[0]), user_ls.index(x[1]))).toDF(
        ["source", "target"])
    # write edges to csv
    df_edges.toPandas().to_csv("edges.csv", header=True, index=False)
    return


def main():
    # Configure Spark
    if not os.path.isdir("checkpoints"):
        os.mkdir("checkpoints")
    conf = SparkConf().setMaster('local').setAppName('connected components')
    sc = SparkContext(conf=conf)
    sqlcontext = SQLContext(sc)
    SparkContext.setCheckpointDir(sc, "checkpoints")

    # The directory for the file
    filename = "q1.txt"

    # Get data in proper format
    data = getData(sc, filename)
    edges = get_edges(data, sqlcontext)
    vertices = get_vertices(data, sqlcontext)
    graph = GraphFrame(vertices, edges)
    connected_components(graph=graph)


if __name__ == '__main__':
    main()
