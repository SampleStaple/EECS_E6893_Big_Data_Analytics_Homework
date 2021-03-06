import pyspark
from pyspark import SparkConf, SparkContext
from pyspark import SQLContext
import os
from graphframes import *


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
    print(user_ls)
    print()
    return


def page_rank(graph):
    """
    run PageRank on graph
    :param graph: Graph contains vertices and edges
    :return:
    """
    print("PageRank:")
    result = graph.pageRank(resetProbability=0.15, tol=0.01)

    # Provide a list of 10 important users (User ID) in this network.
    print("a list of 10 important users (User ID) in this network:")
    user_list = result.vertices.select("id", "pagerank") \
        .orderBy('pagerank',
                 ascending=False).head(10)
    user_ls = [row["id"] for row in user_list]
    print(user_ls)
    print("The most important one is %d" % user_ls[0])
    print()

    # using different parameter settings for PageRank
    print("Using different parameter:")
    result = graph.pageRank(resetProbability=0.1, maxIter=20)
    print("a list of 10 important users (User ID) in this network:")
    user_list = result.vertices.select("id", "pagerank") \
        .orderBy('pagerank',
                 ascending=False).head(10)
    user_ls = [row["id"] for row in user_list]
    print(user_ls)
    print("The most important one is %d" % user_ls[0])


def main():
    # Configure Spark
    if not os.path.isdir("checkpoints"):
        os.mkdir("checkpoints")
    conf = SparkConf().setMaster('local').setAppName('connected components')
    sc = SparkContext(conf=conf)
    sqlcontext = SQLContext(sc)
    SparkContext.setCheckpointDir(sc, "checkpoints")

    # The directory for the file
    filename = "../q1/q1.txt"

    # Get data in proper format
    data = getData(sc, filename)
    edges = get_edges(data, sqlcontext)
    vertices = get_vertices(data, sqlcontext)
    graph = GraphFrame(vertices, edges)
    connected_components(graph=graph)
    page_rank(graph=graph)


if __name__ == '__main__':
    main()
